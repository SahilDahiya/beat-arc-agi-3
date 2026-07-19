from pathlib import Path

import pytest

from beat_arc_agi_3.tools.edit_file import EditFileError, EditFileQuery
from beat_arc_agi_3.workspace import SessionWorkspace


def test_edit_file_replaces_one_exact_occurrence(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    target.write_text("before\nold value\nafter\n", encoding="utf-8")
    workspace = SessionWorkspace(tmp_path)

    output = workspace.edit_file(
        EditFileQuery(
            path="notes.md",
            old_string="old value",
            new_string="new value",
        )
    )

    assert output == "OK: replaced 1 occurrence(s) in notes.md."
    assert target.read_text(encoding="utf-8") == (
        "before\nnew value\nafter\n"
    )


def test_edit_file_fails_when_exact_text_is_absent(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    original = "unchanged\n"
    target.write_text(original, encoding="utf-8")
    workspace = SessionWorkspace(tmp_path)

    with pytest.raises(
        EditFileError,
        match=(
            r"^ERROR: old_string not found \(it must match exactly, "
            r"including whitespace\)\.$"
        ),
    ):
        workspace.edit_file(
            EditFileQuery(
                path="notes.md",
                old_string="missing",
                new_string="replacement",
            )
        )
    assert target.read_text(encoding="utf-8") == original


def test_edit_file_requires_a_unique_match_by_default(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    original = "same\nsame\n"
    target.write_text(original, encoding="utf-8")
    workspace = SessionWorkspace(tmp_path)

    with pytest.raises(
        EditFileError,
        match=(
            "^ERROR: old_string occurs 2 times — add context to make it "
            "unique, or set replace_all=true\\.$"
        ),
    ):
        workspace.edit_file(
            EditFileQuery(
                path="notes.md",
                old_string="same",
                new_string="changed",
            )
        )
    assert target.read_text(encoding="utf-8") == original


def test_edit_file_can_replace_all_exact_matches(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    target.write_text("same\nsame\n", encoding="utf-8")
    workspace = SessionWorkspace(tmp_path)

    output = workspace.edit_file(
        EditFileQuery(
            path="notes.md",
            old_string="same",
            new_string="changed",
            replace_all=True,
        )
    )

    assert output == "OK: replaced 2 occurrence(s) in notes.md."
    assert target.read_text(encoding="utf-8") == "changed\nchanged\n"


def test_edit_file_reports_a_missing_file(tmp_path: Path) -> None:
    workspace = SessionWorkspace(tmp_path)

    with pytest.raises(
        EditFileError,
        match=r"^ERROR: no such file: notes\.md$",
    ):
        workspace.edit_file(
            EditFileQuery(
                path="notes.md",
                old_string="old",
                new_string="new",
            )
        )


def test_edit_file_rejects_paths_outside_the_session(tmp_path: Path) -> None:
    workspace_path = tmp_path / "session"
    workspace_path.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("old", encoding="utf-8")
    workspace = SessionWorkspace(workspace_path)

    with pytest.raises(EditFileError, match="path not writable"):
        workspace.edit_file(
            EditFileQuery(
                path="../secret.txt",
                old_string="old",
                new_string="new",
            )
        )
    assert secret.read_text(encoding="utf-8") == "old"


def test_edit_file_rejects_a_symlink_escape(tmp_path: Path) -> None:
    workspace_path = tmp_path / "session"
    workspace_path.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("old", encoding="utf-8")
    (workspace_path / "link.txt").symlink_to(secret)
    workspace = SessionWorkspace(workspace_path)

    with pytest.raises(EditFileError, match="path not writable"):
        workspace.edit_file(
            EditFileQuery(
                path="link.txt",
                old_string="old",
                new_string="new",
            )
        )
    assert secret.read_text(encoding="utf-8") == "old"


@pytest.mark.parametrize(
    "path",
    ["session.json", "timeline.jsonl", "messages.jsonl"],
)
def test_edit_file_cannot_change_harness_owned_session_state(
    tmp_path: Path,
    path: str,
) -> None:
    target = tmp_path / path
    target.write_text("authoritative", encoding="utf-8")
    workspace = SessionWorkspace(tmp_path)

    with pytest.raises(EditFileError, match="path not writable"):
        workspace.edit_file(
            EditFileQuery(
                path=path,
                old_string="authoritative",
                new_string="corrupted",
            )
        )
    assert target.read_text(encoding="utf-8") == "authoritative"
