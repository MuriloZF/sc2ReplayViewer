from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "SC2 Replay Viewer API"
    api_prefix: str = "/api/v1"
    environment: str = "development"

    model_config = SettingsConfigDict(env_prefix="SC2_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
