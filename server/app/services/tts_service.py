import asyncio
import hashlib
import io
import logging
import os
import struct
import wave
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Maps agent IDs to Gemini TTS voice names
AGENT_VOICE_MAP = {
    "moderator": settings.tts_voice_moderator,
    "skeptic": settings.tts_voice_skeptic,
    "analyst": settings.tts_voice_analyst,
    "contrarian": settings.tts_voice_contrarian,
    "technologist": "Aoede",
    "coo": "Puck",
    "ceo": "Fenrir",
    "cio": "Enceladus",
    "chro": "Zephyr",
    "cco": "Lyra",
}

# Maps agent IDs to Kokoro voice IDs
# Kokoro voices: af_heart, af_bella, af_sarah, af_nicole, am_adam, am_michael,
# bf_emma, bf_isabella, bm_george, bm_lewis, etc.
# Using distinct voices per agent role for variety
KOKORO_VOICE_MAP = {
    "moderator": "af_heart",      # female, warm
    "skeptic": "am_michael",      # male, authoritative
    "analyst": "af_bella",        # female, clear
    "contrarian": "bm_george",    # male (British), distinct
    "technologist": "af_sarah",
    "coo": "am_adam",
    "ceo": "bm_lewis",
    "cio": "af_nicole",
    "chro": "bf_emma",
    "cco": "bf_isabella",
}


def _pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """Convert raw PCM bytes to WAV format."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


class GeminiTTSService:
    """Gemini cloud TTS backend."""

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self._client = None
        if self.api_key:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)

    async def synthesize_to_wav(
        self, text: str, voice_name: str
    ) -> Optional[bytes]:
        if not self._client:
            logger.warning("Gemini TTS client not initialized.")
            return None

        from google.genai import types

        response = await self._client.aio.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        ),
                    ),
                ),
            ),
        )

        parts = response.candidates[0].content.parts
        audio_data = b"".join(
            part.inline_data.data
            for part in parts
            if getattr(part, "inline_data", None) and part.inline_data.data
        )

        logger.info(
            f"Gemini TTS: parts={len(parts)}, pcm_bytes={len(audio_data)}, "
            f"duration_est={len(audio_data) / (24000 * 2):.1f}s"
        )

        return _pcm_to_wav(audio_data, sample_rate=24000)


class KokoroTTSService:
    """Local Kokoro TTS backend (no API key needed)."""

    def __init__(self):
        logger.info("Loading Kokoro TTS model...")
        from kokoro import KPipeline
        self._pipeline = KPipeline(lang_code="a")
        logger.info("Kokoro TTS model loaded.")

    async def synthesize_to_wav(
        self, text: str, voice_name: str
    ) -> Optional[bytes]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._synthesize_sync, text, voice_name
        )

    def _synthesize_sync(self, text: str, voice_name: str) -> Optional[bytes]:
        import numpy as np
        import soundfile as sf



        # Kokoro generates audio in chunks via a generator
        audio_chunks = []
        for _, _, audio in self._pipeline(text, voice=voice_name):
            audio_chunks.append(audio)

        if not audio_chunks:
            logger.warning("Kokoro TTS produced no audio.")
            return None

        audio = np.concatenate(audio_chunks)

        # Kokoro outputs 24kHz float32 — write to WAV via soundfile
        buf = io.BytesIO()
        sf.write(buf, audio, 24000, format="WAV", subtype="PCM_16")
        wav_bytes = buf.getvalue()

        logger.info(
            f"Kokoro TTS: samples={len(audio)}, "
            f"duration={len(audio) / 24000:.1f}s, "
            f"wav_bytes={len(wav_bytes)}"
        )
        return wav_bytes


class TTSService:
    """TTS service that delegates to Gemini or Kokoro based on config."""

    def __init__(self):
        self.storage_dir = settings.storage_dir
        self.backend_name = settings.tts_backend.lower()

        if self.backend_name == "kokoro":
            self._backend = KokoroTTSService()
            self._voice_map = KOKORO_VOICE_MAP
            logger.info("TTS backend: Kokoro (local)")
        else:
            self._backend = GeminiTTSService()
            self._voice_map = AGENT_VOICE_MAP
            logger.info("TTS backend: Gemini (cloud)")

    async def synthesize(
        self,
        agent_id: str,
        text: str,
        session_id: str = "default",
    ) -> Optional[str]:
        """Convert text to speech. Save audio locally and return a URL path."""
        voice_name = self._voice_map.get(agent_id)
        if not voice_name:
            logger.warning(f"No voice configured for agent: {agent_id}")
            return None

        # Generate consistent filename for caching
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        rel_path = f"sessions/{session_id}/tts/{agent_id}_{text_hash}.wav"
        full_path = os.path.join(self.storage_dir, rel_path)

        # Cache hit
        if os.path.exists(full_path):
            logger.info(f"TTS cache hit for {agent_id}: {rel_path}")
            return f"/api/files/{rel_path}"

        try:
            logger.info(
                f"TTS synthesize [{self.backend_name}] for {agent_id}: "
                f"text_len={len(text)}, text='{text[:200]}'"
            )

            wav_bytes = await self._backend.synthesize_to_wav(text, voice_name)
            if wav_bytes is None:
                return None

            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(wav_bytes)

            return f"/api/files/{rel_path}"

        except Exception as e:
            logger.error(f"TTS synthesis failed for {agent_id}: {e}")
            raise

    async def synthesize_sentences(
        self,
        agent_id: str,
        sentences: list[str],
        session_id: str = "default",
    ) -> list[Optional[str]]:
        """TTS multiple sentences in parallel. Returns list of audio URLs."""
        tasks = [self.synthesize(agent_id, s, session_id) for s in sentences]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if isinstance(r, str) else None for r in results]


_tts_singleton: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Return a shared TTSService singleton (avoids reloading Kokoro model)."""
    global _tts_singleton
    if _tts_singleton is None:
        _tts_singleton = TTSService()
    return _tts_singleton
