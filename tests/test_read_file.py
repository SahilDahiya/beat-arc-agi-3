from pathlib import Path

import pytest

from beat_arc_agi_3.tools.read_file import ReadFileError, ReadFileQuery
from beat_arc_agi_3.workspace import SessionWorkspace


def test_read_file_returns_numbered_complete_text(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text(
        "# Notes\n\nconfirmed\n",
        encoding="utf-8",
    )
    workspace = SessionWorkspace(tmp_path)

    output = workspace.read_file(ReadFileQuery(path="notes.md"))

    assert output == (
        "notes.md (3 lines):\n"
        "1\t# Notes\n"
        "2\t\n"
        "3\tconfirmed"
    )


def test_read_file_applies_one_based_offset_and_line_limit(
    tmp_path: Path,
) -> None:
    (tmp_path / "world_model_v5.py").write_text(
        "one\ntwo\nthree\nfour\n",
        encoding="utf-8",
    )
    workspace = SessionWorkspace(tmp_path)

    output = workspace.read_file(
        ReadFileQuery(path="world_model_v5.py", offset=2, limit=2)
    )

    assert output == (
        "world_model_v5.py (4 lines, showing 2-3):\n"
        "2\ttwo\n"
        "3\tthree"
    )


def test_read_file_caps_large_output_at_a_line_boundary(
    tmp_path: Path,
) -> None:
    lines = [f"line-{index:04d}-" + "x" * 100 for index in range(700)]
    (tmp_path / "large.py").write_text("\n".join(lines), encoding="utf-8")
    workspace = SessionWorkspace(tmp_path)

    output = workspace.read_file(
        ReadFileQuery(path="large.py", offset=1, limit=700)
    )

    body, continuation = output.rsplit("\n\n", 1)
    last_rendered_line = int(body.splitlines()[-1].split("\t", 1)[0])
    assert len(body) <= 50_000
    assert continuation == (
        f"(capped — use offset={last_rendered_line + 1} to continue.)"
    )
    assert body.splitlines()[0] == (
        f"large.py (700 lines, showing 1-{last_rendered_line}):"
    )


def test_read_file_reports_a_missing_file(tmp_path: Path) -> None:
    workspace = SessionWorkspace(tmp_path)

    with pytest.raises(
        ReadFileError,
        match=r"^ERROR: no such file: world_model_v5\.py$",
    ):
        workspace.read_file(ReadFileQuery(path="world_model_v5.py"))


def test_read_file_rejects_paths_outside_the_session(
    tmp_path: Path,
) -> None:
    workspace_path = tmp_path / "session"
    workspace_path.mkdir()
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    workspace = SessionWorkspace(workspace_path)

    with pytest.raises(ReadFileError, match="path not readable"):
        workspace.read_file(ReadFileQuery(path="../secret.txt"))


def test_read_file_rejects_a_symlink_escape(tmp_path: Path) -> None:
    workspace_path = tmp_path / "session"
    workspace_path.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    (workspace_path / "link.txt").symlink_to(secret)
    workspace = SessionWorkspace(workspace_path)

    with pytest.raises(ReadFileError, match="path not readable"):
        workspace.read_file(ReadFileQuery(path="link.txt"))
