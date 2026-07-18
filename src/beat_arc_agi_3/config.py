from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Required runtime configuration loaded from the repository environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    arc_api_key: SecretStr
    openai_api_key: SecretStr
    pydantic_ai_model: str
