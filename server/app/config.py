from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database (SQLite by default — no install required)
    database_url: str = "sqlite+aiosqlite:///./highstake.db"

    # External APIs
    anthropic_api_key: str = ""
    deepgram_api_key: str = ""
    elevenlabs_api_key: str = ""

    # Storage (R2/S3)
    storage_endpoint: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_bucket: str = "highstake"
    storage_public_url: str = ""

    # App
    cors_origins: list[str] = ["http://localhost:3000"]
    debug: bool = True

    # ElevenLabs voice IDs per agent
    voice_id_moderator: str = ""
    voice_id_skeptic: str = ""
    voice_id_analyst: str = ""
    voice_id_contrarian: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
