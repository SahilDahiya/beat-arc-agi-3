from pathlib import Path

import pytest

from beat_arc_agi_3.tools.write_file import WriteFileError, WriteFileQuery
from beat_arc_agi_3.workspace import SessionWorkspace


MINIMAL_WORLD_MODEL = '''
def init_state(entry_grid):
    return {}


def predict(state, grid, action, x=None, y=None):
    return grid, {"level_up": False, "dead": False, "win": False}, state


def is_goal(state, grid):
    return False
'''.lstrip()


def test_workspace_reports_when_world_model_exists(tmp_path: Path) -> None:
    workspace = SessionWorkspace(tmp_path)

    assert workspace.has_file("world_model_v5.py") is False

    workspace.write_file(
        WriteFileQuery(
            path="world_model_v5.py",
            content=MINIMAL_WORLD_MODEL,
        )
    )

    assert workspace.has_file("world_model_v5.py") is True


def test_write_file_installs_a_valid_world_model(tmp_path: Path) -> None:
    workspace = SessionWorkspace(tmp_path)

    output = workspace.write_file(
        WriteFileQuery(
            path="world_model_v5.py",
            content=MINIMAL_WORLD_MODEL,
        )
    )

    assert "Installed world model revision" in output
    assert "init_state, predict, is_goal" in output
    assert "Run run_backtest before committing actions." in output


def test_write_file_rejects_an_invalid_world_model_without_persisting_it(
    tmp_path: Path,
) -> None:
    workspace = SessionWorkspace(tmp_path)

    with pytest.raises(
        WriteFileError,
        match="missing required callable: init_state",
    ):
        workspace.write_file(
            WriteFileQuery(
                path="world_model_v5.py",
                content="def predict():\n    pass\n",
            )
        )

    assert not (tmp_path / "world_model_v5.py").exists()


def test_write_file_creates_utf8_text_and_reports_trace_count(
    tmp_path: Path,
) -> None:
    workspace = SessionWorkspace(tmp_path)
    content = "# Notes — exact\n"

    output = workspace.write_file(
        WriteFileQuery(path="notes.md", content=content)
    )

    assert output == f"OK: wrote {len(content)} bytes to notes.md."
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == content


def test_write_file_replaces_the_complete_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    target.write_text("stale\ncontent\n", encoding="utf-8")
    workspace = SessionWorkspace(tmp_path)

    output = workspace.write_file(
        WriteFileQuery(path="notes.md", content="replacement\n")
    )

    assert output == "OK: wrote 12 bytes to notes.md."
    assert target.read_text(encoding="utf-8") == "replacement\n"


def test_write_file_rejects_paths_outside_the_session(tmp_path: Path) -> None:
    workspace_path = tmp_path / "session"
    workspace_path.mkdir()
    workspace = SessionWorkspace(workspace_path)

    with pytest.raises(WriteFileError, match="path not writable"):
        workspace.write_file(
            WriteFileQuery(path="../secret.txt", content="secret")
        )
    assert not (tmp_path / "secret.txt").exists()


def test_write_file_rejects_a_symlink_escape(tmp_path: Path) -> None:
    workspace_path = tmp_path / "session"
    workspace_path.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("original", encoding="utf-8")
    (workspace_path / "link.txt").symlink_to(secret)
    workspace = SessionWorkspace(workspace_path)

    with pytest.raises(WriteFileError, match="path not writable"):
        workspace.write_file(
            WriteFileQuery(path="link.txt", content="overwritten")
        )
    assert secret.read_text(encoding="utf-8") == "original"


@pytest.mark.parametrize(
    "path",
    ["session.json", "timeline.jsonl", "messages.jsonl"],
)
def test_write_file_cannot_replace_harness_owned_session_state(
    tmp_path: Path,
    path: str,
) -> None:
    target = tmp_path / path
    target.write_text("authoritative", encoding="utf-8")
    workspace = SessionWorkspace(tmp_path)

    with pytest.raises(WriteFileError, match="path not writable"):
        workspace.write_file(
            WriteFileQuery(path=path, content="corrupted")
        )
    assert target.read_text(encoding="utf-8") == "authoritative"
