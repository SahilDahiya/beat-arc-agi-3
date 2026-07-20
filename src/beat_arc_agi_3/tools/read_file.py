from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.workspace import SessionWorkspace, WorkspaceEscapeError


MAX_READ_FILE_CHARS = 50_000


class ReadFileQuery(BaseModel):
    """Canonical Schema Harness query for reading a text file."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    offset: int = Field(default=1, ge=1)
    limit: int = Field(default=2000, ge=1)


class ReadFileError(RuntimeError):
    """Raised when a workspace file cannot be read safely."""


def execute_read_file(
    workspace: SessionWorkspace,
    query: ReadFileQuery,
) -> str:
    try:
        resolved = workspace.resolve(query.path)
    except WorkspaceEscapeError as exc:
        raise ReadFileError(
            "ERROR: path not readable (allowed: your session workdir)."
        ) from exc
    if not resolved.path.is_file():
        raise ReadFileError(f"ERROR: no such file: {resolved.label}")

    try:
        lines = resolved.path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ReadFileError(
            f"ERROR: file is not UTF-8: {resolved.label}"
        ) from exc
    except OSError as exc:
        raise ReadFileError(
            f"ERROR: could not read file: {resolved.label}"
        ) from exc

    return _render(
        label=resolved.label,
        lines=lines,
        offset=query.offset,
        limit=query.limit,
    )


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
        candidate_header = _header(
            label=label,
            total=total,
            offset=offset,
            end=line_number,
            complete=(
                offset == 1
                and line_number == total
                and len(candidate_lines) == len(selected)
            ),
        )
        candidate_body = "\n".join([candidate_header, *candidate_lines])
        if len(candidate_body) > MAX_READ_FILE_CHARS:
            if not numbered:
                raise ReadFileError(
                    f"ERROR: line {line_number} exceeds the "
                    f"{MAX_READ_FILE_CHARS}-character read_file output bound."
                )
            capped = True
            break
        numbered = candidate_lines

    if capped:
        while numbered:
            end = offset + len(numbered) - 1
            header = _header(
                label=label,
                total=total,
                offset=offset,
                end=end,
                complete=False,
            )
            continuation = f"(capped — use offset={end + 1} to continue.)"
            output = "\n".join([header, *numbered, "", continuation])
            if len(output) <= MAX_READ_FILE_CHARS:
                return output
            numbered.pop()
        raise ReadFileError(
            f"ERROR: line {offset} exceeds the "
            f"{MAX_READ_FILE_CHARS}-character read_file output bound."
        )

    end = offset + len(numbered) - 1
    complete = offset == 1 and end == total
    header = _header(
        label=label,
        total=total,
        offset=offset,
        end=end,
        complete=complete,
    )
    return "\n".join([header, *numbered])


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
