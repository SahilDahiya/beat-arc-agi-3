from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, ConfigDict, ValidationError


OAUTH_FILE_PATH = Path.home() / ".beat-arc-agi-3" / "oauth.json"


class OAuthStoreError(RuntimeError):
    """Raised when subscription credentials cannot be safely persisted."""


class OpenAICodexCredentials(BaseModel):
    """Refreshable ChatGPT credentials used by the Codex backend."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    access: str
    refresh: str
    expires: int
    account_id: str


class OAuthStoreData(BaseModel):
    """Canonical harness-owned OAuth file shape."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    openai_codex: OpenAICodexCredentials | None = None


def get_openai_codex_credentials() -> OpenAICodexCredentials | None:
    return load_oauth_store().openai_codex


def set_openai_codex_credentials(
    credentials: OpenAICodexCredentials,
) -> None:
    save_oauth_store(OAuthStoreData(openai_codex=credentials))


def clear_openai_codex_credentials() -> None:
    path = OAUTH_FILE_PATH
    if not path.exists() and not path.is_symlink():
        return
    _validate_existing_path(path)
    try:
        path.unlink()
        _fsync_directory(path.parent)
    except OSError as exc:
        raise OAuthStoreError(f"failed to remove OAuth store: {exc}") from exc


def load_oauth_store() -> OAuthStoreData:
    path = OAUTH_FILE_PATH
    if not path.exists() and not path.is_symlink():
        return OAuthStoreData()
    _validate_existing_path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OAuthStoreError(f"failed to read OAuth store: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise OAuthStoreError(f"invalid OAuth store JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise OAuthStoreError("invalid OAuth store data: expected an object")
    normalized = dict(payload)
    if "openai-codex" in normalized:
        normalized["openai_codex"] = normalized.pop("openai-codex")
    try:
        return OAuthStoreData.model_validate(normalized)
    except ValidationError as exc:
        raise OAuthStoreError(f"invalid OAuth store data: {exc}") from exc


def save_oauth_store(data: OAuthStoreData) -> None:
    path = OAUTH_FILE_PATH
    if path.exists() or path.is_symlink():
        _validate_existing_path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.parent.chmod(0o700)
        payload: dict[str, object] = {}
        if data.openai_codex is not None:
            payload["openai-codex"] = data.openai_codex.model_dump()
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.chmod(0o600)
        temporary_path.replace(path)
        _fsync_directory(path.parent)
    except OSError as exc:
        if "temporary_path" in locals():
            temporary_path.unlink(missing_ok=True)
        raise OAuthStoreError(f"failed to write OAuth store: {exc}") from exc


def _validate_existing_path(path: Path) -> None:
    if path.is_symlink():
        raise OAuthStoreError("OAuth store must not be a symlink")
    if not path.is_file():
        raise OAuthStoreError("OAuth store path must be a regular file")
    permissions = stat.S_IMODE(path.stat().st_mode)
    if permissions != 0o600:
        raise OAuthStoreError(
            f"OAuth store permissions must be 0600, got {permissions:04o}"
        )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
