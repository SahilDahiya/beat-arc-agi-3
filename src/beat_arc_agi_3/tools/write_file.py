from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.world_model import (
    WORLD_MODEL_FILENAME,
    WorldModelError,
    WorldModelInfo,
    inspect_world_model_source,
)
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

    model_info: WorldModelInfo | None = None
    if resolved.label == WORLD_MODEL_FILENAME:
        try:
            model_info = inspect_world_model_source(
                query.content,
                workspace_root=workspace.root,
            )
        except WorldModelError as exc:
            raise WriteFileError(f"ERROR: invalid world model: {exc}") from exc

    try:
        workspace.atomic_write_text(resolved.path, query.content)
    except OSError as exc:
        raise WriteFileError(
            f"ERROR: could not write file: {resolved.label}"
        ) from exc
    result = f"OK: wrote {len(query.content)} bytes to {resolved.label}."
    if model_info is not None:
        interfaces = ", ".join(model_info.interfaces)
        result += (
            f" Installed world model revision {model_info.revision[:12]} "
            f"with {interfaces}. Run run_backtest before committing actions."
        )
    return result
