import logging
import time

from app.ws.handler import sio

logger = logging.getLogger(__name__)

# In-memory state for active sessions
session_engines: dict[str, object] = {}  # session_id -> AgentEngine
session_stt: dict[str, object] = {}  # session_id -> STT connection
session_start_times: dict[str, float] = {}  # session_id -> start timestamp


async def handle_audio_chunk(session_id: str, sid: str, data: dict):
    """Forward audio chunk to Deepgram STT stream."""
    if session_id not in session_start_times:
        session_start_times[session_id] = time.time()

    stt = session_stt.get(session_id)
    if stt:
        audio_bytes = data.get("audio", b"")
        if audio_bytes:
            try:
                await stt.send_audio(audio_bytes)
            except Exception as e:
                logger.error(f"STT send error for session {session_id}: {e}")
                await sio.emit("stt_error", {"error": str(e)}, room=f"session_{session_id}")
    else:
        # STT not started yet - initialize it
        await start_stt_for_session(session_id)


async def start_stt_for_session(session_id: str):
    """Start Deepgram STT streaming for a session."""
    from app.config import settings

    if not settings.deepgram_api_key:
        logger.warning(f"No Deepgram API key configured. STT disabled for session {session_id}")
        await sio.emit("stt_error", {"error": "STT not configured"}, room=f"session_{session_id}")
        return

    try:
        from app.services.stt_service import STTService

        stt_service = STTService(settings.deepgram_api_key)

        async def on_transcript(segment: dict):
            # Emit transcript segment to client
            await sio.emit("transcript_segment", segment, room=f"session_{session_id}")

            # Forward to agent engine if final
            engine = session_engines.get(session_id)
            if engine and segment.get("is_final"):
                await engine.on_transcript_segment(segment)

        await stt_service.start_stream(session_id, on_transcript)
        session_stt[session_id] = stt_service
        logger.info(f"STT started for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to start STT for session {session_id}: {e}")
        await sio.emit("stt_error", {"error": str(e)}, room=f"session_{session_id}")


async def stop_stt_for_session(session_id: str):
    """Stop Deepgram STT streaming for a session."""
    stt = session_stt.pop(session_id, None)
    if stt:
        try:
            await stt.stop_stream(session_id)
        except Exception as e:
            logger.error(f"Error stopping STT for session {session_id}: {e}")

    session_engines.pop(session_id, None)
    session_start_times.pop(session_id, None)


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


async def handle_end_session(session_id: str, sid: str):
    """Handle end session event. Generate scoring and debrief."""
    logger.info(f"Session {session_id}: ending")

    await sio.emit(
        "session_state", {"state": "ending"}, room=f"session_{session_id}"
    )

    # Stop STT
    await stop_stt_for_session(session_id)

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


async def initialize_agent_engine(session_id: str):
    """Initialize the agent engine for a session."""
    from app.config import settings
    from app.models.base import async_session_factory
    from app.models.session import Session
    from app.models.deck import Deck
    from sqlalchemy import select

    if not settings.anthropic_api_key:
        logger.warning(f"No Anthropic API key. Agent engine disabled for session {session_id}")
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

        from app.services.claude_client import ClaudeClient
        from app.services.tts_service import TTSService
        from app.services.storage_service import StorageService
        from app.services.agent_engine import AgentEngine

        claude = ClaudeClient(settings.anthropic_api_key)
        storage = StorageService()
        tts = TTSService(settings.elevenlabs_api_key, storage)

        async def emit_callback(event: str, data: dict):
            await sio.emit(event, data, room=f"session_{session_id}")

        engine = AgentEngine(
            session_id=session_id,
            config={
                "interaction_mode": session.interaction_mode,
                "intensity": session.intensity,
                "focus_areas": session.focus_areas,
            },
            deck_manifest=deck_manifest or {},
            claude_client=claude,
            tts_service=tts,
            emit_callback=emit_callback,
        )
        session_engines[session_id] = engine
        session_start_times.setdefault(session_id, time.time())
        logger.info(f"Agent engine initialized for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to initialize agent engine for session {session_id}: {e}")
