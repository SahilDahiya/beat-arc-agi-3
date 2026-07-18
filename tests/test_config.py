from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from beat_arc_agi_3.config import Settings


def test_settings_accept_explicit_runtime_configuration() -> None:
    settings = Settings(
        arc_api_key=SecretStr("arc-test"),
        openai_api_key=SecretStr("openai-test"),
        pydantic_ai_model="openai:test-model",
        sessions_root="./sessions",
    )

    assert settings.arc_api_key.get_secret_value() == "arc-test"
    assert settings.pydantic_ai_model == "openai:test-model"
    assert settings.sessions_root == Path.cwd() / "sessions"


def test_settings_require_an_explicit_model() -> None:
    with pytest.raises(ValidationError, match="pydantic_ai_model"):
        Settings(
            _env_file=None,
            arc_api_key=SecretStr("arc-test"),
            openai_api_key=SecretStr("openai-test"),
            sessions_root="./sessions",
        )


def test_settings_require_an_explicit_sessions_root() -> None:
    with pytest.raises(ValidationError, match="sessions_root"):
        Settings(
            _env_file=None,
            arc_api_key=SecretStr("arc-test"),
            openai_api_key=SecretStr("openai-test"),
            pydantic_ai_model="openai:gpt-5.5",
        )


def test_settings_reject_a_sessions_directory_outside_the_project_root() -> None:
    with pytest.raises(ValidationError, match="directly inside project root"):
        Settings(
            _env_file=None,
            arc_api_key=SecretStr("arc-test"),
            openai_api_key=SecretStr("openai-test"),
            pydantic_ai_model="openai:gpt-5.5",
            sessions_root="./data/sessions",
        )
