import asyncio
import logging
import struct
import math
import re
import time
from typing import Callable, Awaitable

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# VAD thresholds for 16-bit PCM
_RMS_SPEECH_THRESHOLD = 500   # RMS above this = speech detected
_RMS_SILENCE_THRESHOLD = 300  # RMS below this = silence detected
_SILENCE_CHUNKS_FOR_END = 8   # ~800ms of silence to end activity
_MAX_RECONNECTS = 50          # max session reconnects before giving up

# Regex to detect non-Latin scripts (Arabic, Thai, CJK, etc.)
_NON_ENGLISH_RE = re.compile(
    r"[\u0600-\u06FF"   # Arabic
    r"\u0E00-\u0E7F"    # Thai
    r"\u4E00-\u9FFF"    # CJK
    r"\u3040-\u309F"    # Hiragana
    r"\u30A0-\u30FF"    # Katakana
    r"\uAC00-\uD7AF"    # Korean
    r"\u0400-\u04FF"    # Cyrillic
    r"\u0900-\u097F"    # Devanagari
    r"]"
)


def _pcm_rms(pcm_bytes: bytes) -> float:
    """Calculate RMS energy of 16-bit little-endian PCM samples."""
    if len(pcm_bytes) < 2:
        return 0.0
    n_samples = len(pcm_bytes) // 2
    fmt = f"<{n_samples}h"
    try:
        samples = struct.unpack(fmt, pcm_bytes[:n_samples * 2])
    except struct.error:
        return 0.0
    if not samples:
        return 0.0
    sum_sq = sum(s * s for s in samples)
    return math.sqrt(sum_sq / n_samples)


def _is_noise_transcript(text: str) -> bool:
    """Check if transcription is just noise/non-speech or non-English."""
    cleaned = text.strip().lower()
    if cleaned in (
        "<noise>", "(noise)", "[noise]",
        "<silence>", "(silence)", "[silence]",
        "", "ok",
    ):
        return True
    # Filter out non-English transcriptions
    if _NON_ENGLISH_RE.search(cleaned):
        return True
    return False


def _build_live_config():
    """Build the LiveConnectConfig for transcription sessions."""
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Kore"
                )
            ),
            language_code="en-US",
        ),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=True,
            ),
        ),
        system_instruction=(
            "You are a silent transcription assistant. "
            "All input audio is in English. Transcribe only in English. "
            "Do not provide commentary. Reply with only 'ok'."
        ),
    )


class LiveTranscriptionService:
    """Manages a persistent Gemini Live API session for real-time STT.

    Uses manual voice activity detection (VAD) because the native audio
    model's automatic activity detection does not work with
    send_realtime_input.

    The Gemini Live API closes the WebSocket after each model turn, so
    we reconnect lazily when new speech is detected.
    """

    MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

    def __init__(
        self,
        session_id: str,
        api_key: str,
        emit_callback: Callable[[str, dict], Awaitable[None]],
        on_final_transcript: Callable[[dict], Awaitable[None]],
    ):
        self.session_id = session_id
        self.client = genai.Client(
            api_key=api_key, http_options={"api_version": "v1alpha"}
        )
        self.emit_callback = emit_callback
        self.on_final_transcript = on_final_transcript
        self._session = None
        self._session_ctx = None
        self._receive_task: asyncio.Task | None = None
        self._running = False
        self._reconnect_count = 0
        self._connect_lock = asyncio.Lock()
        self._needs_reconnect = False

        # VAD state
        self._speaking = False
        self._silence_count = 0
        self._last_error_time: float = 0

    async def start(self):
        """Open a Live API session and start the receive loop."""
        await self._connect()
        logger.info(
            f"Live transcription started for session {self.session_id}"
        )

    async def _connect(self):
        """Establish a new Gemini Live session and start receiving."""
        async with self._connect_lock:
            # Clean up any existing session
            await self._close_session()

            self._session_ctx = self.client.aio.live.connect(
                model=self.MODEL,
                config=_build_live_config(),
            )
            self._session = await self._session_ctx.__aenter__()
            self._running = True
            self._needs_reconnect = False
            self._receive_task = asyncio.create_task(self._receive_loop())

    async def _ensure_connected(self):
        """Reconnect if the session has closed. Returns True if connected."""
        if not self._needs_reconnect and self._session is not None:
            return True
        if not self._running:
            return False

        self._reconnect_count += 1
        if self._reconnect_count > _MAX_RECONNECTS:
            logger.error(
                f"Session {self.session_id}: max reconnects exceeded"
            )
            self._running = False
            return False

        try:
            await self._connect()
            # Small yield to let the session stabilize before sending audio
            await asyncio.sleep(0.1)
            logger.info(
                f"Session {self.session_id}: reconnected "
                f"(attempt {self._reconnect_count})"
            )
            return True
        except Exception as e:
            logger.error(
                f"Session {self.session_id}: reconnect failed: {e}"
            )
            self._session = None
            return False

    async def _close_session(self):
        """Close the current Gemini session without stopping the service."""
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
            except Exception:
                pass
            self._session = None
            self._session_ctx = None

    async def send_audio(self, pcm_bytes: bytes):
        """Send a chunk of raw PCM audio with manual VAD signaling."""
        if not self._running:
            return

        rms = _pcm_rms(pcm_bytes)

        try:
            if not self._speaking:
                if rms > _RMS_SPEECH_THRESHOLD:
                    # Speech starting — reconnect if needed
                    if self._needs_reconnect or self._session is None:
                        # Cooldown: don't retry reconnect within 1s of last error
                        if time.monotonic() - self._last_error_time < 1.0:
                            return
                        if not await self._ensure_connected():
                            return

                    # Capture session reference to avoid race with _receive_loop
                    session = self._session
                    if session is None:
                        return

                    self._speaking = True
                    self._silence_count = 0
                    logger.info(
                        f"Session {self.session_id}: "
                        f"VAD speech START (rms={rms:.0f})"
                    )
                    await session.send_realtime_input(
                        activity_start=types.ActivityStart()
                    )
                else:
                    # Silence and not speaking — skip
                    return

            # Speaking: send audio — use local ref to avoid race
            session = self._session
            if session is None:
                # Session closed mid-speech, reset VAD
                self._speaking = False
                self._silence_count = 0
                self._needs_reconnect = True
                return

            await session.send_realtime_input(
                audio=types.Blob(
                    data=pcm_bytes, mime_type="audio/pcm;rate=16000"
                )
            )

            if rms < _RMS_SILENCE_THRESHOLD:
                self._silence_count += 1
                if self._silence_count >= _SILENCE_CHUNKS_FOR_END:
                    logger.info(
                        f"Session {self.session_id}: VAD speech END"
                    )
                    await session.send_realtime_input(
                        activity_end=types.ActivityEnd()
                    )
                    self._speaking = False
                    self._silence_count = 0
            else:
                self._silence_count = 0

        except Exception as e:
            logger.warning(
                f"Session {self.session_id}: send audio error: {e}"
            )
            self._session = None
            self._needs_reconnect = True
            self._speaking = False
            self._silence_count = 0
            self._last_error_time = time.monotonic()

    async def _receive_loop(self):
        """Listen for messages from the Live API session."""
        transcript_buffer = ""
        try:
            async for message in self._session.receive():
                if not self._running:
                    break

                server_content = getattr(message, "server_content", None)
                if server_content is None:
                    continue

                # Input transcription (user speech-to-text)
                input_transcription = getattr(
                    server_content, "input_transcription", None
                )
                if input_transcription is not None:
                    text = getattr(input_transcription, "text", "") or ""
                    if text.strip() and not _is_noise_transcript(text):
                        logger.info(
                            f"Session {self.session_id}: "
                            f"transcription: '{text.strip()}'"
                        )
                        transcript_buffer += text
                        segment = {
                            "type": "interim",
                            "text": transcript_buffer,
                            "is_final": False,
                            "confidence": 0.9,
                        }
                        await self.emit_callback(
                            "transcript_segment", segment
                        )

                # Turn completion — finalize transcript
                turn_complete = getattr(
                    server_content, "turn_complete", False
                )
                if turn_complete and transcript_buffer.strip():
                    final_text = transcript_buffer.strip()
                    if not _is_noise_transcript(final_text):
                        logger.info(
                            f"Session {self.session_id}: "
                            f"final transcript: '{final_text}'"
                        )
                        final_segment = {
                            "type": "final",
                            "text": final_text,
                            "is_final": True,
                            "confidence": 0.9,
                        }
                        await self.emit_callback(
                            "transcript_segment", final_segment
                        )
                        await self.on_final_transcript(final_segment)
                    transcript_buffer = ""

        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(
                f"Session {self.session_id}: receive loop error: {e}"
            )

        # Session closed naturally — mark for lazy reconnect
        if self._running:
            logger.info(
                f"Session {self.session_id}: session closed, "
                f"will reconnect on next speech"
            )
            self._needs_reconnect = True
            self._session = None

    async def stop(self):
        """Stop the Live API session and clean up."""
        self._running = False
        await self._close_session()
        logger.info(
            f"Live transcription stopped for session {self.session_id}"
        )
