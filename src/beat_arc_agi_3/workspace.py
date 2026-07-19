from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


MAX_READ_FILE_CHARS = 50_000


class ReadFileQuery(BaseModel):
    """Canonical Schema Harness query for reading a text file."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    offset: int = Field(default=1, ge=1)
    limit: int = Field(default=2000, ge=1)


class ReadFileError(RuntimeError):
    """Raised when a workspace file cannot be read safely."""


class WorkspaceReader(Protocol):
    def read_file(self, query: ReadFileQuery) -> str: ...


@dataclass(frozen=True)
class SessionWorkspace:
    """Read-only file access rooted at one durable agent session."""

    root: Path

    def __post_init__(self) -> None:
        root = self.root.resolve()
        if not root.is_dir():
            raise ValueError(f"workspace root is not a directory: {root}")
        object.__setattr__(self, "root", root)

    def read_file(self, query: ReadFileQuery) -> str:
        path, label = self._resolve(query.path)
        if not path.is_file():
            raise ReadFileError(f"ERROR: no such file: {label}")

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise ReadFileError(f"ERROR: file is not UTF-8: {label}") from exc
        except OSError as exc:
            raise ReadFileError(f"ERROR: could not read file: {label}") from exc

        return self._render(
            label=label,
            lines=lines,
            offset=query.offset,
            limit=query.limit,
        )

    def _resolve(self, requested_path: str) -> tuple[Path, str]:
        raw_path = Path(requested_path).expanduser()
        candidate = raw_path if raw_path.is_absolute() else self.root / raw_path
        resolved = candidate.resolve(strict=False)
        try:
            relative = resolved.relative_to(self.root)
        except ValueError as exc:
            raise ReadFileError(
                "ERROR: path not readable (allowed: your session workdir)."
            ) from exc
        return resolved, relative.as_posix()

    @staticmethod
    def _render(
        *,
        label: str,
        lines: list[str],
        offset: int,
        limit: int,
    ) -> str:
        total = len(lines)
        start_index = offset - 1
        selected = lines[start_index : start_index + limit]
        numbered: list[str] = []
        capped = False

        for line_number, line in enumerate(selected, start=offset):
            candidate_lines = [*numbered, f"{line_number}\t{line}"]
            candidate_end = line_number
            candidate_header = SessionWorkspace._header(
                label=label,
                total=total,
                offset=offset,
                end=candidate_end,
                complete=(
                    offset == 1
                    and candidate_end == total
                    and len(candidate_lines) == len(selected)
                ),
            )
            candidate_body = "\n".join([candidate_header, *candidate_lines])
            if len(candidate_body) > MAX_READ_FILE_CHARS and numbered:
                capped = True
                break
            numbered = candidate_lines

        end = offset + len(numbered) - 1
        complete = offset == 1 and end == total and not capped
        header = SessionWorkspace._header(
            label=label,
            total=total,
            offset=offset,
            end=end,
            complete=complete,
        )
        body = "\n".join([header, *numbered])
        if capped:
            return f"{body}\n\n(capped — use offset={end + 1} to continue.)"
        return body

    @staticmethod
    def _header(
        *,
        label: str,
        total: int,
        offset: int,
        end: int,
        complete: bool,
    ) -> str:
        if complete or total == 0:
            return f"{label} ({total} lines):"
        return f"{label} ({total} lines, showing {offset}-{end}):"
