import base64
import logging
import time
import asyncio

from app.ws.handler import sio

logger = logging.getLogger(__name__)

# In-memory state for active sessions
session_engines: dict[str, object] = {}  # session_id -> AgentEngine
session_start_times: dict[str, float] = {}  # session_id -> start timestamp
session_live_services: dict[str, object] = {}  # session_id -> LiveTranscriptionService
session_locks: dict[str, asyncio.Lock] = {} # session_id -> Lock


async def handle_audio_chunk(session_id: str, sid: str, data: dict):
    """Handle PCM audio chunk from browser AudioWorklet.

    Decodes the base64 PCM data and forwards it to the Gemini Live API
    session for real-time transcription.
    """
    audio_b64 = data.get("audio", "")
    if not audio_b64:
        return
    
    pcm_bytes = None
    try:
        pcm_bytes = base64.b64decode(audio_b64)
    except Exception:
        logger.warning(f"Session {session_id}: invalid base64 audio data")
        return

    if not pcm_bytes:
        return

    # Ensure engine is initialized
    if session_id not in session_engines:
        await initialize_agent_engine(session_id)

    # Ensure live transcription service is running (may need separate retry)
    live_service = session_live_services.get(session_id)
    if not live_service:
        await _ensure_live_service(session_id)
        live_service = session_live_services.get(session_id)

    if live_service:
        await live_service.send_audio(pcm_bytes)
    else:
        logger.warning(
            f"Session {session_id}: no live transcription service available"
        )


async def handle_slide_change(session_id: str, sid: str, data: dict):
    """Handle slide change event from presenter."""
    slide_index = data.get("slideIndex", 0)
    logger.info(f"Session {session_id}: slide changed to {slide_index}")

    engine = session_engines.get(session_id)
    if engine:
        await engine.on_slide_change(slide_index)
    else:
        # Initialize agent engine if not yet started
        await initialize_agent_engine(session_id)
        engine = session_engines.get(session_id)
        if engine:
            await engine.on_slide_change(slide_index)


async def handle_presenter_response(session_id: str, sid: str, data: dict):
    """Handle typed text response from presenter (fallback for voice)."""
    text = data.get("text", "")
    if not text:
        return

    elapsed = time.time() - session_start_times.get(session_id, time.time())

    segment = {
        "type": "final",
        "text": text,
        "start_time": elapsed,
        "end_time": elapsed,
        "confidence": 1.0,
        "is_final": True,
    }

    # Emit as transcript segment
    await sio.emit("transcript_segment", segment, room=f"session_{session_id}")

    # Forward to agent engine
    engine = session_engines.get(session_id)
    if engine:
        await engine.on_transcript_segment(segment)


async def handle_start_session(session_id: str, sid: str):
    """Initialize agent engine and send moderator greeting with TTS."""
    logger.info(f"Session {session_id}: handle_start_session called")

    if session_id not in session_engines:
        logger.info(f"Session {session_id}: initializing agent engine...")
        await initialize_agent_engine(session_id)
        logger.info(f"Session {session_id}: agent engine initialization complete")

    engine = session_engines.get(session_id)
    if engine:
        logger.info(f"Session {session_id}: engine found, emitting moderator greeting")
        greeting = (
            "Good morning everyone. We're here today for a strategic presentation. "
            "Presenter, the floor is yours. We'll hold questions per the agreed format. "
            "Please begin when ready."
        )
        try:
            await engine._emit_moderator(greeting, is_static=True)
            logger.info(f"Session {session_id}: moderator greeting emitted")
        except Exception as e:
            logger.error(f"Session {session_id}: error emitting moderator greeting: {e}")
    else:
        logger.warning(f"Session {session_id}: no engine found, emitting text-only greeting")
        # No engine (no API key) — emit text-only greeting
        await sio.emit(
            "moderator_message",
            {
                "text": "Good morning everyone. We're here today for a strategic presentation. "
                        "Presenter, the floor is yours. Please begin when ready.",
                "audioUrl": None,
                "agentName": "Diana Chen",
                "agentRole": "Moderator",
            },
            room=f"session_{session_id}",
        )


async def handle_end_session(session_id: str, sid: str):
    """Handle end session event. Generate scoring and debrief."""
    logger.info(f"Session {session_id}: ending")

    await sio.emit(
        "session_state", {"state": "ending"}, room=f"session_{session_id}"
    )

    # Generate debrief
    try:
        from app.services.session_finalizer import finalize_session

        await finalize_session(session_id)

        await sio.emit(
            "session_ended",
            {"session_id": session_id, "debrief_ready": True},
            room=f"session_{session_id}",
        )
    except Exception as e:
        logger.error(f"Error finalizing session {session_id}: {e}")
        await sio.emit(
            "session_ended",
            {"session_id": session_id, "debrief_ready": False},
            room=f"session_{session_id}",
        )

    # Cleanup
    await cleanup_session(session_id)


async def cleanup_session(session_id: str):
    """Clean up session state including live transcription service."""
    # Stop live transcription service
    live_service = session_live_services.pop(session_id, None)
    if live_service:
        try:
            await live_service.stop()
        except Exception as e:
            logger.warning(
                f"Session {session_id}: error stopping live transcription: {e}"
            )

    session_engines.pop(session_id, None)
    session_start_times.pop(session_id, None)
    session_locks.pop(session_id, None)


async def initialize_agent_engine(session_id: str):
    """Initialize the agent engine and live transcription for a session."""
    if session_id not in session_locks:
        session_locks[session_id] = asyncio.Lock()
    
    async with session_locks[session_id]:
        if session_id in session_engines:
            return

        from app.config import settings
        from app.models.base import async_session_factory
        from app.models.session import Session
        from app.models.deck import Deck
        from sqlalchemy import select

        if not settings.gemini_api_key:
            logger.warning(f"No Gemini API key. Agent engine disabled for session {session_id}")
            return

        try:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session = result.scalar_one_or_none()
                if not session:
                    return

                deck_manifest = None
                if session.deck_id:
                    deck_result = await db.execute(
                        select(Deck).where(Deck.id == session.deck_id)
                    )
                    deck = deck_result.scalar_one_or_none()
                    if deck:
                        deck_manifest = deck.manifest

            from app.services.llm_client import LLMClient
            from app.services.tts_service import TTSService
            from app.services.agent_engine import AgentEngine
            from app.services.live_transcription import LiveTranscriptionService

            llm = LLMClient(settings.gemini_api_key)
            tts = TTSService()

            async def emit_callback(event: str, data: dict):
                await sio.emit(event, data, room=f"session_{session_id}")

            engine = AgentEngine(
                session_id=session_id,
                config={
                    "interaction_mode": session.interaction_mode,
                    "intensity": session.intensity,
                    "agents": session.agents,
                    "focus_areas": session.focus_areas,
                },
                deck_manifest=deck_manifest or {},
                llm_client=llm,
                tts_service=tts,
                emit_callback=emit_callback,
            )
            session_engines[session_id] = engine
            session_start_times.setdefault(session_id, time.time())
            logger.info(f"Agent engine initialized for session {session_id}")

            # Start live transcription service (separate so engine works even if this fails)
            await _start_live_service_internal(session_id)
        except Exception as e:
            logger.error(f"Failed to initialize agent engine for session {session_id}: {e}")


async def _ensure_live_service(session_id: str):
    """Create and start a live transcription service if one doesn't exist yet."""
    if session_id not in session_locks:
        session_locks[session_id] = asyncio.Lock()

    async with session_locks[session_id]:
        await _start_live_service_internal(session_id)


async def _start_live_service_internal(session_id: str):
    """Internal function to start live service, assumes lock is held if needed."""
    if session_id in session_live_services:
        return

    from app.config import settings
    from app.services.live_transcription import LiveTranscriptionService

    if not settings.gemini_api_key:
        return

    async def emit_callback(event: str, data: dict):
        await sio.emit(event, data, room=f"session_{session_id}")

    async def on_final_transcript(segment: dict):
        eng = session_engines.get(session_id)
        if eng:
            await eng.on_transcript_segment(segment)

    try:
        live_service = LiveTranscriptionService(
            session_id=session_id,
            api_key=settings.gemini_api_key,
            emit_callback=emit_callback,
            on_final_transcript=on_final_transcript,
        )
        await live_service.start()
        session_live_services[session_id] = live_service
        logger.info(f"Live transcription started for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to start live transcription for session {session_id}: {e}")
