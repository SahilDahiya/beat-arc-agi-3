from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from beat_arc_agi_3.config import Settings


def test_settings_accept_explicit_runtime_configuration() -> None:
    settings = Settings(
        arc_api_key=SecretStr("arc-test"),
        pydantic_ai_model="openai-codex:test-model",
        sessions_root="./sessions",
    )

    assert settings.arc_api_key.get_secret_value() == "arc-test"
    assert settings.pydantic_ai_model == "openai-codex:test-model"
    assert settings.sessions_root == Path.cwd() / "sessions"


def test_settings_require_an_explicit_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYDANTIC_AI_MODEL", raising=False)
    with pytest.raises(ValidationError, match="pydantic_ai_model"):
        Settings(
            _env_file=None,
            arc_api_key=SecretStr("arc-test"),
            sessions_root="./sessions",
        )


def test_settings_require_an_explicit_sessions_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SESSIONS_ROOT", raising=False)
    with pytest.raises(ValidationError, match="sessions_root"):
        Settings(
            _env_file=None,
            arc_api_key=SecretStr("arc-test"),
            pydantic_ai_model="openai-codex:gpt-5.5",
        )


def test_settings_reject_a_sessions_directory_outside_the_project_root() -> None:
    with pytest.raises(ValidationError, match="directly inside project root"):
        Settings(
            _env_file=None,
            arc_api_key=SecretStr("arc-test"),
            pydantic_ai_model="openai-codex:gpt-5.5",
            sessions_root="./data/sessions",
        )


def test_settings_reject_non_oauth_model_provider() -> None:
    with pytest.raises(ValidationError, match="openai-codex"):
        Settings(
            _env_file=None,
            arc_api_key=SecretStr("arc-test"),
            pydantic_ai_model="openai:gpt-5.5",
            sessions_root="./sessions",
        )
