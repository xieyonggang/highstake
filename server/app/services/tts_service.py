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


class TTSService:
    """Gemini text-to-speech service with local file storage."""

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.storage_dir = settings.storage_dir

    async def synthesize(
        self,
        agent_id: str,
        text: str,
        session_id: str = "default",
    ) -> Optional[str]:
        """Convert text to speech using Gemini TTS with the agent's voice.
        Save audio locally and return a URL path."""
        if not self.api_key:
            logger.warning("Gemini API key not configured. TTS disabled.")
            return None

        voice_name = AGENT_VOICE_MAP.get(agent_id)
        if not voice_name:
            logger.warning(f"No voice configured for agent: {agent_id}")
            return None

        # Generate consistent filename
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        rel_path = f"tts/{session_id}/{agent_id}_{text_hash}.wav"
        full_path = os.path.join(self.storage_dir, rel_path)

        # Check if file exists (cache hit)
        if os.path.exists(full_path):
            logger.info(f"TTS cache hit for {agent_id}: {rel_path}")
            return f"/api/files/{rel_path}"

        try:
            from google import genai
            from google.genai import types

            logger.info(
                f"TTS synthesize for {agent_id}: "
                f"text_len={len(text)}, text='{text[:200]}'"
            )

            client = genai.Client(api_key=self.api_key)

            response = await client.aio.models.generate_content(
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

            # Extract audio data from all parts of the response
            parts = response.candidates[0].content.parts
            audio_data = b"".join(
                part.inline_data.data
                for part in parts
                if getattr(part, "inline_data", None) and part.inline_data.data
            )

            logger.info(
                f"TTS for {agent_id}: "
                f"parts={len(parts)}, pcm_bytes={len(audio_data)}, "
                f"duration_est={len(audio_data) / (24000 * 2):.1f}s"
            )

            # Convert raw PCM to WAV
            wav_bytes = self._pcm_to_wav(audio_data)

            # Save to local filesystem
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(wav_bytes)

            # Return URL path served by FastAPI
            return f"/api/files/{rel_path}"

        except Exception as e:
            logger.error(f"TTS synthesis failed for {agent_id}: {e}")
            raise

    def _pcm_to_wav(
        self,
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
