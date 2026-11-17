"""Runtime settings, read from environment variables (see .env.example)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://dna:change-me@db:5432/dna"
    openai_api_key: str = ""
    litellm_master_key: str = "sk-admin-change-me"
    gateway_url: str = "http://gateway:4000"
    local_llm_model: str = "gemma3:1b"
    local_llm_url: str = "http://ollama:11434"
    embed_model: str = "intfloat/multilingual-e5-small"
    retention_days: int = 30
    alert_webhook_url: str = ""
    key_rpm_limit: int = 0
    key_max_budget: float = 0.0
    demo_mode: bool = True
    seed_on_start: bool = True
    data_dir: str = ""
    log_dir: str = "/var/dna/logs"
    extension_id: str = ""  # X27: the one browser extension allowed to call the brain (CORS)
    company_ai_url: str = "http://localhost:3000/chat"
    web_url: str = "http://localhost:3000"


settings = Settings()
