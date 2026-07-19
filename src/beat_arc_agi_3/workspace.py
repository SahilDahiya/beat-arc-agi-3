import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from beat_arc_agi_3.tools.edit_file import EditFileQuery
    from beat_arc_agi_3.tools.read_file import ReadFileQuery
    from beat_arc_agi_3.tools.write_file import WriteFileQuery


class WorkspaceEscapeError(RuntimeError):
    """Raised when a requested path resolves outside its Session."""


class WorkspaceWriteDeniedError(RuntimeError):
    """Raised when a write targets harness-owned Session state."""


class WorkspaceTools(Protocol):
    def has_file(self, path: str) -> bool: ...

    def read_file(self, query: "ReadFileQuery") -> str: ...

    def write_file(self, query: "WriteFileQuery") -> str: ...

    def edit_file(self, query: "EditFileQuery") -> str: ...


@dataclass(frozen=True)
class ResolvedWorkspacePath:
    path: Path
    label: str


@dataclass(frozen=True)
class SessionWorkspace:
    """Shared safe filesystem boundary for one durable agent session."""

    root: Path

    _RESERVED_FILES = frozenset(
        {"session.json", "timeline.jsonl", "messages.jsonl"}
    )

    def __post_init__(self) -> None:
        root = self.root.resolve()
        if not root.is_dir():
            raise ValueError(f"workspace root is not a directory: {root}")
        object.__setattr__(self, "root", root)

    def resolve(self, requested_path: str) -> ResolvedWorkspacePath:
        raw_path = Path(requested_path).expanduser()
        candidate = raw_path if raw_path.is_absolute() else self.root / raw_path
        resolved = candidate.resolve(strict=False)
        try:
            relative = resolved.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceEscapeError(requested_path) from exc
        return ResolvedWorkspacePath(
            path=resolved,
            label=relative.as_posix(),
        )

    def resolve_writable(self, requested_path: str) -> ResolvedWorkspacePath:
        resolved = self.resolve(requested_path)
        if resolved.label in self._RESERVED_FILES:
            raise WorkspaceWriteDeniedError(resolved.label)
        return resolved

    def has_file(self, path: str) -> bool:
        return self.resolve(path).path.is_file()

    def atomic_write_text(self, path: Path, content: str) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.replace(path)
            self._sync_directory(path.parent)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    def read_file(self, query: "ReadFileQuery") -> str:
        from beat_arc_agi_3.tools.read_file import execute_read_file

        return execute_read_file(self, query)

    def write_file(self, query: "WriteFileQuery") -> str:
        from beat_arc_agi_3.tools.write_file import execute_write_file

        return execute_write_file(self, query)

    def edit_file(self, query: "EditFileQuery") -> str:
        from beat_arc_agi_3.tools.edit_file import execute_edit_file

        return execute_edit_file(self, query)

    @staticmethod
    def _sync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
