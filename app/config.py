"""Centralized, validated application configuration."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


def _load_environment() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    example_path = Path(__file__).resolve().parents[1] / ".env.example"

    if env_path.exists():
        load_dotenv(env_path, override=False)
        return

    if example_path.exists():
        load_dotenv(example_path, override=False)
        return

    load_dotenv()


_load_environment()


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    rapidapi_key: str | None = os.getenv("RAPIDAPI_KEY")
    reddit_client_id: str | None = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret: str | None = os.getenv("REDDIT_CLIENT_SECRET")
    jwt_secret: str = os.getenv("JWT_SECRET", "development-only-change-me-before-production")
    allowed_origins: tuple[str, ...] = tuple(
        origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if origin.strip()
    )
    topic_check_interval_minutes: int = int(
        os.getenv("TOPIC_CHECK_INTERVAL_MINUTES", "360")
    )


settings = Settings()
