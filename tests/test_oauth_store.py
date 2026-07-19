import json
import stat
from pathlib import Path

import pytest

from beat_arc_agi_3 import oauth_store
from beat_arc_agi_3.oauth_store import (
    OAuthStoreError,
    OpenAICodexCredentials,
    clear_openai_codex_credentials,
    get_openai_codex_credentials,
    set_openai_codex_credentials,
)


def credentials() -> OpenAICodexCredentials:
    return OpenAICodexCredentials(
        access="access-token",
        refresh="refresh-token",
        expires=1_760_000_000_000,
        account_id="acct-123",
    )


def test_oauth_store_round_trips_with_private_permissions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "oauth.json"
    monkeypatch.setattr(oauth_store, "OAUTH_FILE_PATH", path)

    set_openai_codex_credentials(credentials())

    assert get_openai_codex_credentials() == credentials()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "openai-codex": credentials().model_dump()
    }


def test_oauth_store_rejects_insecure_permissions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "oauth.json"
    monkeypatch.setattr(oauth_store, "OAUTH_FILE_PATH", path)
    set_openai_codex_credentials(credentials())
    path.chmod(0o644)

    with pytest.raises(OAuthStoreError, match="permissions must be 0600"):
        get_openai_codex_credentials()


def test_oauth_store_rejects_unknown_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "oauth.json"
    monkeypatch.setattr(oauth_store, "OAUTH_FILE_PATH", path)
    path.write_text('{"openai-codex": null, "unexpected": true}\n')
    path.chmod(0o600)

    with pytest.raises(OAuthStoreError, match="invalid OAuth store data"):
        get_openai_codex_credentials()


def test_clear_oauth_credentials_removes_the_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "oauth.json"
    monkeypatch.setattr(oauth_store, "OAUTH_FILE_PATH", path)
    set_openai_codex_credentials(credentials())

    clear_openai_codex_credentials()

    assert get_openai_codex_credentials() is None
    assert not path.exists()
