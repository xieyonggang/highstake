import hashlib
import logging
from typing import Optional

import httpx

from app.config import settings
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# Maps agent IDs to ElevenLabs voice IDs (configured via settings)
AGENT_VOICE_MAP = {
    "moderator": settings.voice_id_moderator,
    "skeptic": settings.voice_id_skeptic,
    "analyst": settings.voice_id_analyst,
    "contrarian": settings.voice_id_contrarian,
}


class TTSService:
    """ElevenLabs text-to-speech service."""

    def __init__(self, api_key: str, storage: StorageService):
        self.api_key = api_key
        self.storage = storage
        self.base_url = "https://api.elevenlabs.io/v1"

    async def synthesize(self, agent_id: str, text: str) -> Optional[str]:
        """Convert text to speech using the agent's voice profile.
        Upload audio to storage and return a signed URL."""
        if not self.api_key:
            logger.warning("ElevenLabs API key not configured. TTS disabled.")
            return None

        voice_id = AGENT_VOICE_MAP.get(agent_id)
        if not voice_id:
            logger.warning(f"No voice ID configured for agent: {agent_id}")
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}/stream",
                    headers={
                        "xi-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                        },
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                audio_bytes = response.content

            # Upload to storage
            text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
            key = f"tts/{agent_id}/{text_hash}.mp3"
            await self.storage.upload(key, audio_bytes, "audio/mpeg")
            return await self.storage.get_signed_url(key)

        except Exception as e:
            logger.error(f"TTS synthesis failed for {agent_id}: {e}")
            raise
