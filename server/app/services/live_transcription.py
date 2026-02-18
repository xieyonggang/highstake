import asyncio
import io
import logging
import math
import re
import struct
import time
import wave
from typing import Callable, Awaitable

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
    r"\u0980-\u09FF"    # Bengali
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
    cleaned = _strip_noise_tokens(text).strip().lower()
    if cleaned in (
        "<noise>", "(noise)", "[noise]",
        "<silence>", "(silence)", "[silence]",
        "", "ok", "um", "uh", "hmm", "ah",
    ):
        return True
    # Very short transcripts (< 4 alphabetic chars) are almost always noise
    alpha_only = re.sub(r"[^a-zA-Z]", "", cleaned)
    if len(alpha_only) < 4:
        return True
    # Filter out non-English transcriptions
    if _NON_ENGLISH_RE.search(cleaned):
        return True
    return False


# Regex to strip noise/silence tokens embedded in transcripts
_NOISE_TOKEN_RE = re.compile(
    r"\s*<(?:noise|silence)>\s*|\s*\((?:noise|silence)\)\s*|\s*\[(?:noise|silence)\]\s*",
    re.IGNORECASE,
)


def _strip_noise_tokens(text: str) -> str:
    """Remove <noise>, (noise), [noise] etc. tokens from transcript text."""
    return _NOISE_TOKEN_RE.sub(" ", text).strip()


# ---------------------------------------------------------------------------
# Gemini Live backend
# ---------------------------------------------------------------------------

def _build_live_config():
    """Build the LiveConnectConfig for transcription sessions."""
    from google.genai import types

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

    MODEL = "gemini-2.5-flash-native-audio-latest"

    def __init__(
        self,
        session_id: str,
        api_key: str,
        emit_callback: Callable[[str, dict], Awaitable[None]],
        on_final_transcript: Callable[[dict], Awaitable[None]],
    ):
        from google import genai

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
        self._reconnect_lock = asyncio.Lock()
        self._needs_reconnect = False

        # VAD state
        self._speaking = False
        self._silence_count = 0
        self._last_error_time: float = 0

    async def start(self):
        """Open a Live API session and start the receive loop."""
        self._running = True
        logger.info(
            f"Session {self.session_id}: starting live transcription, "
            f"model={self.MODEL}"
        )
        await self._connect()
        logger.info(
            f"Session {self.session_id}: live transcription started, "
            f"session={self._session is not None}, "
            f"receive_task={self._receive_task is not None}"
        )

    async def _connect(self):
        """Establish a new Gemini Live session and start receiving."""
        async with self._connect_lock:
            if not self._running:
                logger.warning(
                    f"Session {self.session_id}: _connect called but not running"
                )
                return

            # Clean up any existing session
            await self._close_session()

            logger.info(
                f"Session {self.session_id}: connecting to Gemini Live API "
                f"(model={self.MODEL})..."
            )
            try:
                self._session_ctx = self.client.aio.live.connect(
                    model=self.MODEL,
                    config=_build_live_config(),
                )
                self._session = await self._session_ctx.__aenter__()
                self._needs_reconnect = False
                self._receive_task = asyncio.create_task(self._receive_loop())
                logger.info(
                    f"Session {self.session_id}: Gemini Live session "
                    f"connected successfully"
                )
            except Exception as e:
                logger.error(
                    f"Session {self.session_id}: _connect failed: {e}"
                )
                self._session = None
                self._session_ctx = None
                self._needs_reconnect = True
                raise

    async def _ensure_connected(self):
        """Reconnect if the session has closed. Returns True if connected."""
        if not self._needs_reconnect and self._session is not None:
            return True
        if not self._running:
            return False

        # Serialize reconnect attempts to prevent concurrent racing
        async with self._reconnect_lock:
            # Re-check after acquiring lock — another coroutine may have reconnected
            if not self._needs_reconnect and self._session is not None:
                return True
            if not self._running:
                return False

            self._reconnect_count += 1
            if self._reconnect_count > _MAX_RECONNECTS:
                logger.error(
                    f"Session {self.session_id}: max reconnects exceeded "
                    f"({self._reconnect_count}), stopping transcription"
                )
                self._running = False
                self._session = None
                self._needs_reconnect = False
                return False

            try:
                await self._connect()
                await asyncio.sleep(0.2)
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
                self._needs_reconnect = True
                self._last_error_time = time.monotonic()
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

    _send_count: int = 0  # Tracks total chunks sent for logging

    async def send_audio(self, pcm_bytes: bytes):
        """Send a chunk of raw PCM audio with manual VAD signaling."""
        from google.genai import types

        if not self._running:
            if self._send_count == 0:
                logger.warning(
                    f"Session {self.session_id}: send_audio called but "
                    f"service not running"
                )
            return

        self._send_count += 1
        rms = _pcm_rms(pcm_bytes)

        # Log first chunk and periodic status
        if self._send_count == 1:
            logger.info(
                f"Session {self.session_id}: first send_audio call, "
                f"pcm_bytes={len(pcm_bytes)}, rms={rms:.0f}, "
                f"session={self._session is not None}, "
                f"needs_reconnect={self._needs_reconnect}, "
                f"speaking={self._speaking}"
            )
        elif self._send_count % 500 == 0:
            logger.info(
                f"Session {self.session_id}: send_audio #{self._send_count}, "
                f"rms={rms:.0f}, speaking={self._speaking}, "
                f"session={self._session is not None}, "
                f"needs_reconnect={self._needs_reconnect}, "
                f"reconnect_count={self._reconnect_count}"
            )

        try:
            if not self._speaking:
                if rms > _RMS_SPEECH_THRESHOLD:
                    # Speech starting — reconnect if needed
                    if self._needs_reconnect or self._session is None:
                        # Cooldown: don't retry reconnect within 1s of last error
                        if time.monotonic() - self._last_error_time < 3.0:
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
        msg_count = 0
        logger.info(
            f"Session {self.session_id}: receive_loop started, "
            f"waiting for messages..."
        )
        try:
            async for message in self._session.receive():
                if not self._running:
                    break

                msg_count += 1
                server_content = getattr(message, "server_content", None)
                if server_content is None:
                    # Log non-server_content messages (setup, tool_call, etc.)
                    if msg_count <= 5:
                        msg_type = type(message).__name__
                        attrs = [a for a in dir(message) if not a.startswith('_')]
                        logger.debug(
                            f"Session {self.session_id}: receive msg #{msg_count} "
                            f"type={msg_type}, attrs={attrs[:10]}"
                        )
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
                    final_text = _strip_noise_tokens(transcript_buffer.strip())
                    if final_text and not _is_noise_transcript(final_text):
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
                        try:
                            await self.on_final_transcript(final_segment)
                        except Exception as e:
                            logger.error(
                                f"Session {self.session_id}: "
                                f"on_final_transcript error: {e}"
                            )
                    transcript_buffer = ""

        except asyncio.CancelledError:
            logger.info(
                f"Session {self.session_id}: receive_loop cancelled "
                f"after {msg_count} messages"
            )
            return
        except Exception as e:
            logger.error(
                f"Session {self.session_id}: receive loop error after "
                f"{msg_count} messages: {e}",
                exc_info=True,
            )

        # Session closed naturally — mark for lazy reconnect
        if self._running:
            logger.info(
                f"Session {self.session_id}: session closed after "
                f"{msg_count} messages, will reconnect on next speech"
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


# ---------------------------------------------------------------------------
# Whisper (faster-whisper) backend
# ---------------------------------------------------------------------------

# Shared faster-whisper model instance (loaded once, reused across sessions)
_whisper_model = None
_whisper_model_lock = asyncio.Lock()


async def _get_whisper_model():
    """Lazy-load the faster-whisper model (singleton)."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    async with _whisper_model_lock:
        if _whisper_model is not None:
            return _whisper_model

        # Prevent OpenMP crash/deadlock from duplicate libiomp5 (numpy + ctranslate2)
        import os
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        os.environ["OMP_NUM_THREADS"] = "1"

        from app.config import settings
        model_size = settings.whisper_model
        logger.info(f"Loading faster-whisper model '{model_size}'...")

        from faster_whisper import WhisperModel
        loop = asyncio.get_event_loop()
        _whisper_model = await loop.run_in_executor(
            None,
            lambda: WhisperModel(
                model_size, device="cpu", compute_type="auto",
                cpu_threads=1,
            ),
        )
        logger.info(f"Faster-whisper model '{model_size}' loaded.")
        return _whisper_model


class WhisperTranscriptionService:
    """Local STT using faster-whisper with the same VAD as the Gemini backend.

    Accumulates PCM audio during speech (detected by VAD), then transcribes
    the full utterance when silence is detected.
    """

    SAMPLE_RATE = 16000

    def __init__(
        self,
        session_id: str,
        emit_callback: Callable[[str, dict], Awaitable[None]],
        on_final_transcript: Callable[[dict], Awaitable[None]],
    ):
        self.session_id = session_id
        self.emit_callback = emit_callback
        self.on_final_transcript = on_final_transcript
        self._running = False

        # VAD state
        self._speaking = False
        self._silence_count = 0
        self._audio_buffer = bytearray()
        self._send_count = 0

        # Transcription task queue
        self._transcribe_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._transcribe_task: asyncio.Task | None = None

    async def start(self):
        """Pre-load the whisper model and start the transcription worker."""
        self._running = True
        # Pre-load model in background
        await _get_whisper_model()
        self._transcribe_task = asyncio.create_task(self._transcribe_worker())
        logger.info(
            f"Session {self.session_id}: Whisper transcription started"
        )

    async def send_audio(self, pcm_bytes: bytes):
        """Process a chunk of raw 16kHz 16-bit PCM audio with VAD."""
        if not self._running:
            return

        self._send_count += 1
        rms = _pcm_rms(pcm_bytes)

        if self._send_count == 1:
            logger.info(
                f"Session {self.session_id}: [whisper] first audio chunk, "
                f"pcm_bytes={len(pcm_bytes)}, rms={rms:.0f}"
            )
        elif self._send_count % 500 == 0:
            logger.info(
                f"Session {self.session_id}: [whisper] chunk #{self._send_count}, "
                f"rms={rms:.0f}, speaking={self._speaking}, "
                f"buffer={len(self._audio_buffer)} bytes"
            )

        if not self._speaking:
            if rms > _RMS_SPEECH_THRESHOLD:
                self._speaking = True
                self._silence_count = 0
                self._audio_buffer.clear()
                self._audio_buffer.extend(pcm_bytes)
                logger.info(
                    f"Session {self.session_id}: "
                    f"[whisper] VAD speech START (rms={rms:.0f})"
                )
            return

        # Currently speaking — accumulate audio
        self._audio_buffer.extend(pcm_bytes)

        if rms < _RMS_SILENCE_THRESHOLD:
            self._silence_count += 1
            if self._silence_count >= _SILENCE_CHUNKS_FOR_END:
                # Speech ended — submit for transcription
                logger.info(
                    f"Session {self.session_id}: [whisper] VAD speech END, "
                    f"buffer={len(self._audio_buffer)} bytes "
                    f"({len(self._audio_buffer) / (self.SAMPLE_RATE * 2):.1f}s)"
                )
                audio_data = bytes(self._audio_buffer)
                self._audio_buffer.clear()
                self._speaking = False
                self._silence_count = 0
                await self._transcribe_queue.put(audio_data)
        else:
            self._silence_count = 0

    async def _transcribe_worker(self):
        """Background worker that transcribes audio buffers from the queue."""
        while self._running:
            try:
                audio_data = await asyncio.wait_for(
                    self._transcribe_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                duration_s = len(audio_data) / (self.SAMPLE_RATE * 2)
                logger.info(
                    f"Session {self.session_id}: [whisper] worker dequeued "
                    f"{len(audio_data)} bytes ({duration_s:.1f}s), "
                    f"transcribing..."
                )
                text = await self._transcribe(audio_data)
                logger.info(
                    f"Session {self.session_id}: [whisper] _transcribe returned: "
                    f"'{text[:80] if text else ''}' (len={len(text)})"
                )
                if not text:
                    logger.info(
                        f"Session {self.session_id}: [whisper] empty "
                        f"transcription for {len(audio_data)} bytes "
                        f"({len(audio_data) / (self.SAMPLE_RATE * 2):.1f}s)"
                    )
                    continue
                if _is_noise_transcript(text):
                    logger.info(
                        f"Session {self.session_id}: [whisper] filtered "
                        f"as noise: '{text}'"
                    )
                    continue
                text = _strip_noise_tokens(text)
                logger.info(
                    f"Session {self.session_id}: "
                    f"[whisper] transcript: '{text}'"
                )

                # Emit interim + final (Whisper gives full utterance at once)
                interim_segment = {
                    "type": "interim",
                    "text": text,
                    "is_final": False,
                    "confidence": 0.9,
                }
                await self.emit_callback(
                    "transcript_segment", interim_segment
                )

                final_segment = {
                    "type": "final",
                    "text": text,
                    "is_final": True,
                    "confidence": 0.9,
                }
                await self.emit_callback(
                    "transcript_segment", final_segment
                )

                try:
                    await self.on_final_transcript(final_segment)
                except Exception as e:
                    logger.error(
                        f"Session {self.session_id}: "
                        f"on_final_transcript error: {e}"
                    )
            except Exception as e:
                logger.error(
                    f"Session {self.session_id}: "
                    f"[whisper] transcription error: {e}",
                    exc_info=True,
                )

    # Dedicated executor so stuck transcriptions don't block other async work
    _executor = None

    @classmethod
    def _get_executor(cls):
        if cls._executor is None:
            from concurrent.futures import ThreadPoolExecutor
            cls._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="whisper")
        return cls._executor

    async def _transcribe(self, pcm_bytes: bytes) -> str:
        """Transcribe PCM audio bytes using faster-whisper."""
        import numpy as np

        model = await _get_whisper_model()

        # Convert 16-bit PCM to float32 numpy array
        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
        samples /= 32768.0
        duration_s = len(samples) / self.SAMPLE_RATE

        def _do_transcribe():
            import time as _time
            t0 = _time.monotonic()
            segs, info = model.transcribe(
                samples,
                language="en",
                beam_size=1,
                vad_filter=True,
                without_timestamps=True,
                condition_on_previous_text=False,
                no_speech_threshold=0.6,
                compression_ratio_threshold=2.4,
            )
            parts = []
            for seg in segs:
                text = seg.text.strip()
                if text and seg.no_speech_prob < 0.8:
                    parts.append(text)
            result = " ".join(parts)
            elapsed = _time.monotonic() - t0
            logger.info(
                f"Session {self.session_id}: [whisper] transcribed "
                f"{duration_s:.1f}s audio in {elapsed:.1f}s → "
                f"'{result[:100]}'"
            )
            return result

        timeout = max(15.0, duration_s * 5)
        try:
            text = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    self._get_executor(), _do_transcribe
                ),
                timeout=timeout,
            )
            return text.strip()
        except asyncio.TimeoutError:
            logger.warning(
                f"Session {self.session_id}: [whisper] transcription timed out "
                f"({timeout:.0f}s) for {duration_s:.1f}s audio"
            )
            return ""

    async def stop(self):
        """Stop the transcription service."""
        self._running = False
        if self._transcribe_task and not self._transcribe_task.done():
            self._transcribe_task.cancel()
            try:
                await self._transcribe_task
            except asyncio.CancelledError:
                pass
        logger.info(
            f"Whisper transcription stopped for session {self.session_id}"
        )
