"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # GitHub App settings
    github_app_id: int
    github_private_key: str
    github_webhook_secret: str

    # Scoring thresholds
    warning_threshold: int = -10
    close_threshold: int = -25

    # Application settings
    log_level: str = "INFO"
    debug: bool = False


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()  # type: ignore[call-arg]  # pydantic-settings loads from env
