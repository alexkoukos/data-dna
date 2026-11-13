"""Runtime settings, read from environment variables (see .env.example)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://dna:change-me@db:5432/dna"
    openai_api_key: str = ""
    local_llm_model: str = "gemma3:1b"
    embed_model: str = "intfloat/multilingual-e5-small"
    retention_days: int = 30
    demo_mode: bool = True


settings = Settings()
