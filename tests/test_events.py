import json
from pathlib import Path

import pytest

from beat_arc_agi_3.events import (
    BfsCompletedEvent,
    DeliberationStartedEvent,
    EventJournal,
    EventJournalCorruptionError,
    ToolCompletedEvent,
    ToolStartedEvent,
)
from beat_arc_agi_3.schemas import ArcAction


def test_event_journal_appends_contiguous_durable_entries(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    journal = EventJournal.create(path, session_id="run-001")

    first = journal.append(
        turn=1,
        event=DeliberationStartedEvent(
            summary="Deliberating over turn 1 observation"
        ),
    )
    second = journal.append(
        turn=1,
        event=ToolStartedEvent(
            summary="Backtesting world_model_v5.py",
            tool_call_id="call-1",
            tool_name="run_backtest",
        ),
    )
    third = journal.append(
        turn=1,
        event=ToolCompletedEvent(
            summary="Backtest completed",
            tool_call_id="call-1",
            tool_name="run_backtest",
            duration_ms=17,
        ),
    )

    assert [first.seq, second.seq, third.seq] == [1, 2, 3]
    assert all(entry.session_id == "run-001" for entry in journal.entries())
    assert all(entry.timestamp.tzinfo is not None for entry in journal.entries())
    assert [
        json.loads(line)["event"]["type"]
        for line in path.read_text(encoding="utf-8").splitlines()
    ] == ["deliberation_started", "tool_started", "tool_completed"]

    reopened = EventJournal(path, session_id="run-001")
    assert reopened.entries() == journal.entries()


def test_event_journal_rejects_non_contiguous_persisted_sequence(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.jsonl"
    journal = EventJournal.create(path, session_id="run-001")
    journal.append(
        turn=1,
        event=DeliberationStartedEvent(summary="Deliberating"),
    )
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["seq"] = 3
    path.write_text(json.dumps(raw) + "\n", encoding="utf-8")

    with pytest.raises(EventJournalCorruptionError, match="sequence 3; expected 1"):
        EventJournal(path, session_id="run-001")


def test_event_journal_rejects_a_different_session_identity(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.jsonl"
    journal = EventJournal.create(path, session_id="run-001")
    journal.append(
        turn=1,
        event=DeliberationStartedEvent(summary="Deliberating"),
    )

    with pytest.raises(EventJournalCorruptionError, match="belongs to session"):
        EventJournal(path, session_id="run-002")


def test_event_journal_round_trips_bfs_outcome_evidence(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    journal = EventJournal.create(path, session_id="run-001")
    journal.append(
        turn=2,
        event=BfsCompletedEvent(
            summary="BFS found a level-up plan",
            revision="revision-1",
            target="level_up",
            status="found",
            max_depth=12,
            node_budget=500,
            expanded_nodes=27,
            distinct_states=19,
            depth=3,
            actions=(ArcAction(action="ACTION1"),),
        ),
    )

    reopened = EventJournal(path, session_id="run-001")
    event = reopened.entries()[0].event
    assert event.type == "bfs_completed"
    assert event.status == "found"
    assert event.depth == 3
    assert event.actions == (ArcAction(action="ACTION1"),)
