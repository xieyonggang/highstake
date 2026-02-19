from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database (SQLite by default — no install required)
    database_url: str = "sqlite+aiosqlite:///./highstake.db"

    # Gemini API (single key for LLM + TTS)
    gemini_api_key: str = ""

    # OpenAI API (for TTS and STT)
    openai_api_key: str = ""

    # Local file storage
    storage_dir: str = "./data"

    # App
    cors_origins: list[str] = ["http://localhost:3000"]
    debug: bool = True

    # Agent warm-up: minimum presenter words before agents start evaluating
    agent_warmup_words: int = 50

    # TTS backend: "gemini", "kokoro", or "openai"
    tts_backend: str = "openai"

    # STT backend: "gemini", "whisper", or "openai"
    stt_backend: str = "openai"

    # Whisper model size for local STT (e.g. "base.en", "small.en", "medium.en")
    whisper_model: str = "base.en"

    # Gemini TTS voice names (30 built-in voices available)
    tts_voice_moderator: str = "Kore"
    tts_voice_skeptic: str = "Charon"
    tts_voice_analyst: str = "Leda"
    tts_voice_contrarian: str = "Orus"

    # OpenAI TTS voice names (alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer)
    openai_tts_voice_moderator: str = "nova"
    openai_tts_voice_skeptic: str = "onyx"
    openai_tts_voice_analyst: str = "sage"
    openai_tts_voice_contrarian: str = "echo"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
