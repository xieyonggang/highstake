from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database (SQLite by default — no install required)
    database_url: str = "sqlite+aiosqlite:///./highstake.db"

    # Gemini API (single key for LLM + TTS)
    gemini_api_key: str = ""

    # Local file storage
    storage_dir: str = "./data"

    # App
    cors_origins: list[str] = ["http://localhost:3000"]
    debug: bool = True

    # Gemini TTS voice names (30 built-in voices available)
    tts_voice_moderator: str = "Kore"
    tts_voice_skeptic: str = "Charon"
    tts_voice_analyst: str = "Leda"
    tts_voice_contrarian: str = "Orus"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
