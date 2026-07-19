from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.workspace import (
    SessionWorkspace,
    WorkspaceEscapeError,
    WorkspaceWriteDeniedError,
)


class WriteFileQuery(BaseModel):
    """Canonical Schema Harness query for replacing a complete text file."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    content: str


class WriteFileError(RuntimeError):
    """Raised when a workspace file cannot be written safely."""


def execute_write_file(
    workspace: SessionWorkspace,
    query: WriteFileQuery,
) -> str:
    try:
        resolved = workspace.resolve_writable(query.path)
    except (WorkspaceEscapeError, WorkspaceWriteDeniedError) as exc:
        raise WriteFileError(
            "ERROR: path not writable (allowed: your session workdir)."
        ) from exc

    try:
        workspace.atomic_write_text(resolved.path, query.content)
    except OSError as exc:
        raise WriteFileError(
            f"ERROR: could not write file: {resolved.label}"
        ) from exc
    return (
        f"OK: wrote {len(query.content)} bytes to {resolved.label}."
    )
