from pathlib import Path

import pytest
from pydantic_ai import ModelRequest, UserPromptPart

from beat_arc_agi_3.session import (
    Session,
    SessionCorruptionError,
    SessionExistsError,
    SessionNotFoundError,
)


def test_session_create_owns_metadata_and_timeline(tmp_path: Path) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai:gpt-5.5",
    )

    assert session.path == tmp_path / "run-001"
    assert session.metadata.session_id == "run-001"
    assert session.metadata.game_id == "test-game"
    assert session.metadata.model == "openai:gpt-5.5"
    assert session.metadata.created_at.tzinfo is not None
    assert session.metadata_path.is_file()
    assert session.timeline.path == session.path / "timeline.jsonl"
    assert session.timeline.transitions() == ()
    assert session.conversation.path == session.path / "messages.jsonl"
    assert session.conversation.messages() == ()


def test_session_reopens_the_same_validated_timeline(tmp_path: Path) -> None:
    created = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai:gpt-5.5",
    )

    reopened = Session.open(sessions_root=tmp_path, session_id="run-001")

    assert reopened.metadata == created.metadata
    assert reopened.timeline.game_id == "test-game"


def test_session_reopens_persisted_agent_messages(tmp_path: Path) -> None:
    created = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="openai:gpt-5.5",
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
        model="openai:gpt-5.5",
    )

    with pytest.raises(SessionExistsError, match="already exists"):
        Session.create(
            sessions_root=tmp_path,
            session_id="run-001",
            game_id="test-game",
            model="openai:gpt-5.5",
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
            model="openai:gpt-5.5",
        )


def test_session_open_rejects_corrupt_metadata(tmp_path: Path) -> None:
    session_path = tmp_path / "run-001"
    session_path.mkdir()
    (session_path / "session.json").write_text("not-json", encoding="utf-8")
    (session_path / "timeline.jsonl").touch()

    with pytest.raises(SessionCorruptionError, match="session metadata"):
        Session.open(sessions_root=tmp_path, session_id="run-001")
