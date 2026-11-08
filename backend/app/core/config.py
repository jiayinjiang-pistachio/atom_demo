from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Pistachio Atom API"
    version: str = "0.1.0"
    environment: str = "local"
    api_prefix: str = "/api/v1"

    database_url: str = "mysql+asyncmy://atom:atom@127.0.0.1:3307/atom?charset=utf8mb4"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    frontend_origin: str = "http://localhost:5173"
    preview_origin: str = "http://localhost:8000"
    preview_host: str = "localhost"

    llm_provider: str = "deepseek"
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_mode: str = "auto"

    max_runs_per_guest_day: int = 20
    max_steps: int = 24
    max_file_bytes: int = 32768
    max_project_bytes: int = 262144


@lru_cache
def get_settings() -> Settings:
    return Settings()
