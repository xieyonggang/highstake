import asyncio
import logging
from typing import Callable, Awaitable

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class LiveTranscriptionService:
    """Manages a persistent Gemini Live API session for real-time STT.

    One instance per presentation session. Receives raw PCM audio chunks
    from the client, forwards them to the Gemini Live API, and emits
    transcript segments back via callbacks.
    """

    def __init__(
        self,
        session_id: str,
        api_key: str,
        emit_callback: Callable[[str, dict], Awaitable[None]],
        on_final_transcript: Callable[[dict], Awaitable[None]],
    ):
        self.session_id = session_id
        self.client = genai.Client(api_key=api_key)
        self.emit_callback = emit_callback
        self.on_final_transcript = on_final_transcript
        self._session = None
        self._session_ctx = None
        self._receive_task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Open a Live API session and start the receive loop."""
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Aoede"
                    )
                )
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    prefix_padding_ms=20,
                    silence_duration_ms=500,
                ),
            ),
            system_instruction=(
                "You are a silent transcription assistant. "
                "Do not provide commentary. Reply with only 'ok'."
            ),
        )
        self._session_ctx = self.client.aio.live.connect(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            config=config,
        )
        self._session = await self._session_ctx.__aenter__()
        self._running = True
        self._receive_task = asyncio.create_task(self._receive_loop())
        logger.info(f"Live transcription started for session {self.session_id}")

    async def send_audio(self, pcm_bytes: bytes):
        """Send a chunk of raw PCM audio to the Live API session."""
        if not self._session or not self._running:
            return
        try:
            await self._session.send_realtime_input(
                audio=types.Blob(
                    data=pcm_bytes, mime_type="audio/pcm;rate=16000"
                )
            )
            # logger.debug(f"Sent {len(pcm_bytes)} bytes of audio to session {self.session_id}")
        except Exception as e:
            logger.warning(
                f"Session {self.session_id}: error sending audio: {e}"
            )

    async def _receive_loop(self):
        """Listen for messages from the Live API session."""
        transcript_buffer = ""
        logger.info(f"Session {self.session_id}: Starting receive loop")
        try:
            async for message in self._session.receive():
                if not self._running:
                    break

                # Check for input transcription in server_content
                server_content = getattr(message, "server_content", None)
                if server_content is None:
                    continue

                # Extract input transcription (what the user said)
                input_transcription = getattr(
                    server_content, "model_turn", None
                )
                
                # Check for real input transcription
                real_input_transcription = getattr(
                    server_content, "input_transcription", None
                )
                
                if real_input_transcription:
                    text = getattr(real_input_transcription, "text", "") or ""
                    logger.info(f"Session {self.session_id}: Received input transcription text: '{text}'")
                    if text.strip():
                        transcript_buffer += text
                        # Emit interim transcript segment
                        segment = {
                            "type": "interim",
                            "text": transcript_buffer,
                            "is_final": False,
                            "confidence": 0.9,
                        }
                        logger.info(f"Session {self.session_id}: Emitting interim segment: {segment}")
                        await self.emit_callback(
                            "transcript_segment", segment
                        )

                # Check for turn completion (user stopped speaking)
                turn_complete = getattr(server_content, "turn_complete", False)
                if turn_complete:
                    logger.info(f"Session {self.session_id}: Turn complete. Buffer: '{transcript_buffer}'")

                if turn_complete and transcript_buffer.strip():
                    final_segment = {
                        "type": "final",
                        "text": transcript_buffer.strip(),
                        "is_final": True,
                        "confidence": 0.9,
                    }
                    logger.info(f"Session {self.session_id}: Emitting final segment: {final_segment}")
                    await self.emit_callback(
                        "transcript_segment", final_segment
                    )
                    await self.on_final_transcript(final_segment)
                    transcript_buffer = ""

        except asyncio.CancelledError:
            logger.info(
                f"Live transcription receive loop cancelled "
                f"for session {self.session_id}"
            )
        except Exception as e:
            logger.error(
                f"Live transcription receive loop error "
                f"for session {self.session_id}: {e}"
            )

    async def stop(self):
        """Stop the Live API session and clean up."""
        self._running = False

        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._session_ctx:
            try:
                await self._session_ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(
                    f"Session {self.session_id}: error closing live session: {e}"
                )
            self._session = None
            self._session_ctx = None

        logger.info(
            f"Live transcription stopped for session {self.session_id}"
        )
