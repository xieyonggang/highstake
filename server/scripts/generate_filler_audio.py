"""Generate pre-baked filler audio for each agent voice.

Run once:  cd server && python generate_filler_audio.py
"""

import io
import os
import sys
import wave
import logging

sys.path.append(os.getcwd())

from app.config import settings
from app.services.tts_service import AGENT_VOICE_MAP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FILLER_PHRASES = {
    "skeptic": [
        "Hmm, let me consider that.",
        "I see, but I have some concerns.",
        "That's an interesting point.",
    ],
    "analyst": [
        "Let me think about those numbers.",
        "I see your reasoning.",
        "That's worth examining further.",
    ],
    "contrarian": [
        "Interesting perspective.",
        "Hmm, I'm not entirely convinced.",
        "Let me push back on that a bit.",
    ],
}

TARGET_DIR = "app/resources/agent_fillers"


def _pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def main():
    if not settings.gemini_api_key:
        logger.error("GEMINI_API_KEY is not set.")
        return

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)

    for agent_id, phrases in FILLER_PHRASES.items():
        voice_name = AGENT_VOICE_MAP.get(agent_id)
        if not voice_name:
            logger.warning(f"No voice for {agent_id}, skipping")
            continue

        agent_dir = os.path.join(TARGET_DIR, agent_id)
        os.makedirs(agent_dir, exist_ok=True)

        for i, text in enumerate(phrases):
            output_path = os.path.join(agent_dir, f"filler_{i}.wav")
            if os.path.exists(output_path):
                logger.info(f"Already exists: {output_path}")
                continue

            logger.info(
                f"Generating {agent_id} filler_{i} "
                f"(voice={voice_name}): '{text}'"
            )
            try:
                response = client.models.generate_content(
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

                audio_data = b"".join(
                    part.inline_data.data
                    for part in response.candidates[0].content.parts
                    if getattr(part, "inline_data", None)
                    and part.inline_data.data
                )

                wav_bytes = _pcm_to_wav(audio_data)
                with open(output_path, "wb") as f:
                    f.write(wav_bytes)

                duration = len(audio_data) / (24000 * 2)
                logger.info(
                    f"Saved {output_path} ({duration:.1f}s)"
                )
            except Exception as e:
                logger.error(f"Failed for {agent_id} filler_{i}: {e}")


if __name__ == "__main__":
    main()
