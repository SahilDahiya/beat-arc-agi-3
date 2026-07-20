import hashlib
from pathlib import Path

import pytest
from arcengine import FrameData, GameAction, GameState
from pydantic_ai import ModelRequest, UserPromptPart

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.events import (
    ActionStartedEvent,
    DeliberationStartedEvent,
    WorldModelSnapshottedEvent,
)
from beat_arc_agi_3.restart import (
    ReplayDivergenceError,
    RestartUnsafeError,
    create_restarted_session,
    replay_session,
)
from beat_arc_agi_3.schemas import ArcAction
from beat_arc_agi_3.session import Session
from beat_arc_agi_3.tools.write_file import WriteFileQuery



def frame(value: int, *, levels_completed: int = 0) -> FrameData:
    return FrameData(
        game_id="test-game",
        frame=[[[value]]],
        state=GameState.NOT_FINISHED,
        levels_completed=levels_completed,
        win_levels=2,
        available_actions=[1],
    )


class FakeEnvironment:
    def __init__(self, results: list[FrameData]) -> None:
        self.results = results
        self.current = frame(0)
        self.actions: list[tuple[GameAction, dict[str, int] | None]] = []

    @property
    def action_space(self) -> list[GameAction]:
        return [GameAction.ACTION1]

    def reset(self) -> FrameData:
        return self.current

    def step(
        self,
        action: GameAction,
        data: dict[str, int] | None = None,
    ) -> FrameData:
        self.actions.append((action, data))
        self.current = self.results.pop(0)
        return self.current


WORLD_MODEL = """def init_state(entry_grid):
    return {}

def predict(state, grid, action, x=None, y=None):
    return grid, {"level_up": False, "dead": False, "win": False}, state

def is_goal(state, grid):
    return False
"""


def parent_session(tmp_path: Path) -> Session:
    parent = Session.create(
        sessions_root=tmp_path,
        session_id="parent-001",
        game_id="test-game",
        model="test:model",
    )
    parent.timeline.initialize(frame_observation(0))
    parent.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=frame_observation(1),
        model_revision="revision-1",
        prediction=None,
    )
    parent.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=frame_observation(2),
        model_revision="revision-2",
        prediction=None,
    )
    parent.conversation.append(
        [ModelRequest(parts=[UserPromptPart("durable prior reasoning")])]
    )
    parent.workspace.write_file(
        WriteFileQuery(path="notes.md", content="# carried notes\n")
    )
    parent.workspace.write_file(
        WriteFileQuery(path="world_model_v5.py", content=WORLD_MODEL)
    )
    parent.workspace.write_file(
        WriteFileQuery(path="analysis.txt", content="carried evidence\n")
    )
    return parent


def frame_observation(value: int):
    from beat_arc_agi_3.schemas import GameObservation

    return GameObservation.from_frame(frame(value))


def test_restart_replays_exactly_and_creates_lineaged_child(tmp_path: Path) -> None:
    parent = parent_session(tmp_path)
    environment = FakeEnvironment([frame(1), frame(2)])
    adapter = ArcGameAdapter(environment)

    checkpoint = replay_session(
        parent=parent,
        adapter=adapter,
        initial_observation=adapter.reset(),
    )
    child = create_restarted_session(
        parent=parent,
        sessions_root=tmp_path,
        session_id="child-001",
        model="test:model",
        checkpoint=checkpoint,
    )

    assert checkpoint == frame_observation(2)
    assert environment.actions == [
        (GameAction.ACTION1, None),
        (GameAction.ACTION1, None),
    ]
    assert child.metadata.origin == "replay_restart"
    assert child.metadata.parent_session_id == "parent-001"
    assert child.metadata.replayed_transitions == 2
    assert child.timeline.transitions() == parent.timeline.transitions()
    assert child.conversation.messages() == parent.conversation.messages()
    assert child.workspace.read_text("notes.md") == "# carried notes\n"
    assert child.workspace.read_text("world_model_v5.py") == WORLD_MODEL
    assert child.workspace.read_text("analysis.txt") == "carried evidence\n"
    assert [entry.event.type for entry in child.events.entries()] == [
        "session_started",
        "session_restarted",
    ]
    reopened = Session.open(sessions_root=tmp_path, session_id="child-001")
    assert reopened.metadata == child.metadata
    assert reopened.timeline.transitions() == parent.timeline.transitions()


def test_restart_fails_before_child_creation_on_replay_divergence(
    tmp_path: Path,
) -> None:
    parent = parent_session(tmp_path)
    environment = FakeEnvironment([frame(9)])
    adapter = ArcGameAdapter(environment)

    with pytest.raises(ReplayDivergenceError, match="transition 0"):
        replay_session(
            parent=parent,
            adapter=adapter,
            initial_observation=adapter.reset(),
        )


def test_restart_refuses_an_uncertain_arc_action(tmp_path: Path) -> None:
    parent = parent_session(tmp_path)
    parent.events.append(
        turn=3,
        event=ActionStartedEvent(
            summary="action call began",
            action_number=3,
            transition_index=2,
            action=ArcAction(action="ACTION1"),
            model_revision="revision-2",
            prediction_mode="unchecked",
        ),
    )
    adapter = ArcGameAdapter(FakeEnvironment([frame(1), frame(2)]))

    with pytest.raises(RestartUnsafeError, match="uncertain ARC action"):
        replay_session(
            parent=parent,
            adapter=adapter,
            initial_observation=adapter.reset(),
        )


def test_restart_marks_a_provider_valid_pending_deliberation(
    tmp_path: Path,
) -> None:
    parent = parent_session(tmp_path)
    parent.events.append(
        turn=3,
        event=DeliberationStartedEvent(summary="pending deliberation"),
    )
    adapter = ArcGameAdapter(FakeEnvironment([frame(1), frame(2)]))
    checkpoint = replay_session(
        parent=parent,
        adapter=adapter,
        initial_observation=adapter.reset(),
    )

    child = create_restarted_session(
        parent=parent,
        sessions_root=tmp_path,
        session_id="child-001",
        model="test:model",
        checkpoint=checkpoint,
    )

    assert child.metadata.resumes_pending_deliberation is True
    restarted = child.events.entries()[1].event
    assert restarted.type == "session_restarted"
    assert restarted.resumes_pending_deliberation is True


def test_restart_inherits_and_revalidates_cleared_level_snapshots(
    tmp_path: Path,
) -> None:
    parent = Session.create(
        sessions_root=tmp_path,
        session_id="parent-001",
        game_id="test-game",
        model="test:model",
    )
    parent.workspace.write_file(
        WriteFileQuery(path="world_model_v5.py", content=WORLD_MODEL)
    )
    revision = hashlib.sha256(WORLD_MODEL.encode()).hexdigest()
    parent.timeline.initialize(frame_observation(0))
    after = frame_observation_with_level(1, levels_completed=1)
    parent.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=after,
        model_revision=revision,
        prediction=None,
    )
    snapshot = parent.snapshot_world_model(
        cleared_level=0,
        revision=revision,
    )
    parent.events.append(
        turn=1,
        event=WorldModelSnapshottedEvent(
            summary="snapshotted cleared level",
            cleared_level=0,
            revision=revision,
            prediction_status="unchecked",
            path=snapshot.relative_to(parent.path).as_posix(),
        ),
    )
    environment = FakeEnvironment([frame(1, levels_completed=1)])
    adapter = ArcGameAdapter(environment)
    checkpoint = replay_session(
        parent=parent,
        adapter=adapter,
        initial_observation=adapter.reset(),
    )

    child = create_restarted_session(
        parent=parent,
        sessions_root=tmp_path,
        session_id="child-001",
        model="test:model",
        checkpoint=checkpoint,
    )

    reopened = Session.open(sessions_root=tmp_path, session_id="child-001")
    assert (reopened.path / "snapshots/cleared_level_0.py").read_text() == (
        WORLD_MODEL
    )


def frame_observation_with_level(value: int, *, levels_completed: int):
    from beat_arc_agi_3.schemas import GameObservation

    return GameObservation.from_frame(
        frame(value, levels_completed=levels_completed)
    )
