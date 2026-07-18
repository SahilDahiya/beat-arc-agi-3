from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
    sessions_root: Path

    @field_validator("sessions_root")
    @classmethod
    def validate_sessions_root(cls, path: Path) -> Path:
        resolved = (path if path.is_absolute() else PROJECT_ROOT / path).resolve()
        if resolved.parent != PROJECT_ROOT:
            raise ValueError(
                f"sessions_root must be directly inside project root {PROJECT_ROOT}"
            )
        return resolved
