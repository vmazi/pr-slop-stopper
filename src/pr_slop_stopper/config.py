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

    @property
    def webhook_secret(self) -> str:
        """Return webhook secret with whitespace stripped."""
        return self.github_webhook_secret.strip()

    @property
    def private_key(self) -> str:
        """Return private key with only trailing whitespace stripped.

        PEM files require internal newlines for proper formatting.
        Only strip trailing newlines added by podman secrets.
        """
        return self.github_private_key.rstrip()

    # Scoring thresholds
    warning_threshold: int = -10
    close_threshold: int = -25

    # Application settings
    log_level: str = "INFO"
    debug: bool = False


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()  # type: ignore[call-arg]  # pydantic-settings loads from env
