from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # API settings
    API_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Instagram Scraper API"

    # Instagram scraper settings
    INSTAGRAM_ACCOUNT: str = "nasa"
    POSTS_LIMIT: int = 10
    CHECK_HASHTAG: str = "#Space"

    # Selenium settings
    HEADLESS_BROWSER: bool = True
    BROWSER_TIMEOUT: int = 30

    # Celery settings
    CELERY_BROKER_URL: str | None = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str | None = "redis://localhost:6379/0"

    # Telegram bot settings
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_IDS: list[str] = []

    @field_validator("TELEGRAM_CHAR_IDS", mode="before")
    @classmethod
    def validate_chat_ids(cls, value) -> list[str]:
        """Validate and convert TELEGRAM_CHAT_IDS to a list."""
        if isinstance(value, str) and value:
            return [chat_id.strip() for chat_id in value.split(",")]
        if isinstance(value, (list, set)):
            return list(value)
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
