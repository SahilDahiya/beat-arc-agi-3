import hashlib
from pathlib import Path

import pytest
from pydantic_ai import ModelRequest, UserPromptPart

from beat_arc_agi_3.events import WorldModelSnapshottedEvent
from beat_arc_agi_3.session import (
    Session,
    SessionCorruptionError,
    SessionExistsError,
    SessionNotFoundError,
    SessionSnapshotError,
)


def test_session_create_owns_metadata_and_timeline(tmp_path: Path) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )

    assert session.path == tmp_path / "run-001"
    assert session.metadata.session_id == "run-001"
    assert session.metadata.game_id == "test-game"
    assert session.metadata.model == "openai-codex:gpt-5.5"
    assert session.metadata.created_at.tzinfo is not None
    assert session.metadata_path.is_file()
    assert session.timeline.path == session.path / "timeline.jsonl"
    assert session.timeline.transitions() == ()
    assert session.conversation.path == session.path / "messages.jsonl"
    assert session.conversation.messages() == ()
    assert session.events.path == session.path / "events.jsonl"
    assert [entry.event.type for entry in session.events.entries()] == [
        "session_started"
    ]
    assert session.events.entries()[0].event.game_id == "test-game"
    assert session.workspace.root == session.path
    notes = (session.path / "notes.md").read_text(encoding="utf-8")
    assert notes.startswith("# Notes - living scientific scratchpad\n")
    assert "## Confirmed mechanics" in notes
    assert "## Current level" in notes
    assert "## Level-entry grounding" in notes
    assert "### Observed facts" in notes
    assert "### Hypotheses" in notes
    assert "### Known unknowns" in notes
    assert "### Cheapest discriminating probe" in notes
    assert "## Temporary goal" in notes
    assert "- Selected hypothesis:" in notes
    assert "- Competing hypothesis:" in notes
    assert "- Predicate:" in notes
    assert "- Evidence:" in notes
    assert "- Falsifier:" in notes
    assert "## Decision mode" in notes
    assert "- Mode: goal_search | discriminating_experiment" in notes
    assert "- Why:" in notes
    assert "## Hypotheses to test" in notes
    assert "## Confirmed facts" in notes
    assert "## Current plan" in notes


def test_session_reopens_the_same_validated_timeline(tmp_path: Path) -> None:
    created = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )

    reopened = Session.open(sessions_root=tmp_path, session_id="run-001")

    assert reopened.metadata == created.metadata
    assert reopened.timeline.game_id == "test-game"
    assert reopened.events.entries() == created.events.entries()


def test_session_reopens_persisted_agent_messages(tmp_path: Path) -> None:
    created = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )
    message = ModelRequest(parts=[UserPromptPart("first turn")])
    created.conversation.append([message])

    reopened = Session.open(sessions_root=tmp_path, session_id="run-001")

    assert reopened.conversation.messages() == (message,)


def test_session_create_fails_when_the_session_exists(tmp_path: Path) -> None:
    Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )

    with pytest.raises(SessionExistsError, match="already exists"):
        Session.create(
            sessions_root=tmp_path,
            session_id="run-001",
            game_id="test-game",
            model="openai-codex:gpt-5.5",
        )


def test_session_open_fails_when_the_session_is_missing(tmp_path: Path) -> None:
    with pytest.raises(SessionNotFoundError, match="does not exist"):
        Session.open(sessions_root=tmp_path, session_id="missing")


@pytest.mark.parametrize("session_id", ["../escape", ".", "..", "with/slash"])
def test_session_rejects_unsafe_identifiers(
    tmp_path: Path, session_id: str
) -> None:
    with pytest.raises(ValueError, match="session_id"):
        Session.create(
            sessions_root=tmp_path,
            session_id=session_id,
            game_id="test-game",
            model="openai-codex:gpt-5.5",
        )


def test_session_open_rejects_corrupt_metadata(tmp_path: Path) -> None:
    session_path = tmp_path / "run-001"
    session_path.mkdir()
    (session_path / "session.json").write_text("not-json", encoding="utf-8")
    (session_path / "timeline.jsonl").touch()

    with pytest.raises(SessionCorruptionError, match="session metadata"):
        Session.open(sessions_root=tmp_path, session_id="run-001")


def test_session_open_requires_the_canonical_event_journal(tmp_path: Path) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )
    session.events.path.unlink()

    with pytest.raises(SessionCorruptionError, match="event journal"):
        Session.open(sessions_root=tmp_path, session_id="run-001")


def test_session_open_requires_canonical_utf8_notes(tmp_path: Path) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )
    (session.path / "notes.md").unlink()

    with pytest.raises(SessionCorruptionError, match="notes"):
        Session.open(sessions_root=tmp_path, session_id="run-001")


def test_session_open_rejects_non_utf8_notes(tmp_path: Path) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )
    (session.path / "notes.md").write_bytes(b"\xff")

    with pytest.raises(SessionCorruptionError, match="notes"):
        Session.open(sessions_root=tmp_path, session_id="run-001")


def test_session_snapshots_an_exact_world_model_revision_once(
    tmp_path: Path,
) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )
    source = b"def init_state(entry_grid):\n    return {}\n"
    (session.path / "world_model_v5.py").write_bytes(source)
    revision = hashlib.sha256(source).hexdigest()

    snapshot = session.snapshot_world_model(
        cleared_level=0,
        revision=revision,
    )

    assert snapshot == session.path / "snapshots" / "cleared_level_0.py"
    assert snapshot.read_bytes() == source
    with pytest.raises(SessionSnapshotError, match="already exists"):
        session.snapshot_world_model(cleared_level=0, revision=revision)


def test_session_snapshot_rejects_a_revision_other_than_the_source(
    tmp_path: Path,
) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )
    (session.path / "world_model_v5.py").write_text(
        "def init_state(entry_grid):\n    return {}\n",
        encoding="utf-8",
    )

    with pytest.raises(SessionSnapshotError, match="revision"):
        session.snapshot_world_model(cleared_level=0, revision="wrong")


def test_session_open_validates_journaled_snapshot_artifacts(
    tmp_path: Path,
) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )
    source = b"def init_state(entry_grid):\n    return {}\n"
    (session.path / "world_model_v5.py").write_bytes(source)
    revision = hashlib.sha256(source).hexdigest()
    snapshot = session.snapshot_world_model(
        cleared_level=0,
        revision=revision,
    )
    session.events.append(
        turn=1,
        event=WorldModelSnapshottedEvent(
            summary="Snapshotted cleared level 0 model",
            cleared_level=0,
            revision=revision,
            prediction_status="exact",
            path="snapshots/cleared_level_0.py",
        ),
    )
    snapshot.unlink()

    with pytest.raises(SessionCorruptionError, match="snapshot"):
        Session.open(sessions_root=tmp_path, session_id="run-001")


def test_session_open_rejects_an_unjournaled_snapshot(tmp_path: Path) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai-codex:gpt-5.5",
    )
    source = b"def init_state(entry_grid):\n    return {}\n"
    (session.path / "world_model_v5.py").write_bytes(source)
    session.snapshot_world_model(
        cleared_level=0,
        revision=hashlib.sha256(source).hexdigest(),
    )

    with pytest.raises(SessionCorruptionError, match="snapshot evidence"):
        Session.open(sessions_root=tmp_path, session_id="run-001")
