from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "SC2 Replay Viewer API"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    map_cache_dir: Path = Path(".cache/maps")
    win_probability_model_dir: Path = (
        Path(__file__).resolve().parents[2] / "models" / "XGBClassifier"
    )

    model_config = SettingsConfigDict(env_prefix="SC2_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
