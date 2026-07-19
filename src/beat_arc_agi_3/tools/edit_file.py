from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.workspace import (
    SessionWorkspace,
    WorkspaceEscapeError,
    WorkspaceWriteDeniedError,
)


class EditFileQuery(BaseModel):
    """Canonical Schema Harness query for exact text replacement."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    old_string: str
    new_string: str
    replace_all: bool = False


class EditFileError(RuntimeError):
    """Raised when an exact workspace edit cannot be applied safely."""


def execute_edit_file(
    workspace: SessionWorkspace,
    query: EditFileQuery,
) -> str:
    try:
        resolved = workspace.resolve_writable(query.path)
    except (WorkspaceEscapeError, WorkspaceWriteDeniedError) as exc:
        raise EditFileError(
            "ERROR: path not writable (allowed: your session workdir)."
        ) from exc
    if not resolved.path.is_file():
        raise EditFileError(f"ERROR: no such file: {resolved.label}")

    try:
        content = resolved.path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise EditFileError(
            f"ERROR: file is not UTF-8: {resolved.label}"
        ) from exc
    except OSError as exc:
        raise EditFileError(
            f"ERROR: could not read file: {resolved.label}"
        ) from exc

    occurrences = content.count(query.old_string)
    if occurrences == 0:
        raise EditFileError(
            "ERROR: old_string not found (it must match exactly, including "
            "whitespace)."
        )
    if occurrences > 1 and not query.replace_all:
        raise EditFileError(
            f"ERROR: old_string occurs {occurrences} times — add context to "
            "make it unique, or set replace_all=true."
        )

    replacement_count = occurrences if query.replace_all else 1
    updated = content.replace(
        query.old_string,
        query.new_string,
        replacement_count,
    )
    try:
        workspace.atomic_write_text(resolved.path, updated)
    except OSError as exc:
        raise EditFileError(
            f"ERROR: could not write file: {resolved.label}"
        ) from exc
    return (
        f"OK: replaced {replacement_count} occurrence(s) in "
        f"{resolved.label}."
    )
