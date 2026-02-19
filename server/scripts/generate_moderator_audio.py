import asyncio
import io
import os
import sys
import wave
import logging

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_moderator_audio():
    if not settings.gemini_api_key:
        logger.error("Error: GEMINI_API_KEY is not set.")
        return

    text = (
        "Good morning everyone. We're here today for a strategic presentation. "
        "Presenter, the floor is yours. We'll hold questions per the agreed format. "
        "Please begin when ready."
    )
    
    voice_name = settings.tts_voice_moderator # "Kore"

    target_dir = "app/resources/common_assets"
    os.makedirs(target_dir, exist_ok=True)
    output_path = os.path.join(target_dir, "moderator_greeting.wav")

    logger.info(f"Generating audio for moderator using voice '{voice_name}'...")
    logger.info(f"Text: {text}")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)

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

        # Extract audio data from the response
        audio_data = response.candidates[0].content.parts[0].inline_data.data

        # Convert raw PCM to WAV
        wav_bytes = _pcm_to_wav(audio_data)

        with open(output_path, "wb") as f:
            f.write(wav_bytes)

        logger.info(f"Successfully saved moderator audio to: {output_path}")

    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        import traceback
        traceback.print_exc()

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

if __name__ == "__main__":
    asyncio.run(generate_moderator_audio())
