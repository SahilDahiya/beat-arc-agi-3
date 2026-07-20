import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from arc_agi import OperationMode
from arcengine import FrameData, GameAction, GameState
from pydantic import SecretStr
from pydantic_ai import ModelMessage, ModelRequest, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.agent import build_agent
from beat_arc_agi_3.events import (
    ActionStartedEvent,
    DeliberationStartedEvent,
    EnvironmentRestartedEvent,
)
from beat_arc_agi_3.loop import (
    LoopPolicy,
    LoopRestartContext,
    LoopResult,
    run_agent_loop,
)
from beat_arc_agi_3.process import RestartProcessConfig, restart_process
from beat_arc_agi_3.restart import (
    ReplayDivergenceError,
    RestartUnsafeError,
    replay_session,
    resumes_pending_deliberation,
)
from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.session import Session
from beat_arc_agi_3.tools.write_file import WriteFileQuery


WORLD_MODEL = """def init_state(entry_grid):
    return {}

def predict(state, grid, action, x=None, y=None):
    return grid, {"level_up": False, "dead": False, "win": False}, state

def is_goal(state, grid):
    return False
"""


def frame(
    value: int,
    *,
    state: GameState = GameState.NOT_FINISHED,
) -> FrameData:
    return FrameData(
        game_id="test-game",
        frame=[[[value]]],
        state=state,
        levels_completed=0,
        win_levels=2,
        available_actions=[1],
    )


def observation(value: int) -> GameObservation:
    return GameObservation.from_frame(frame(value))


class FakeEnvironment:
    def __init__(self, results: list[FrameData]) -> None:
        self.results = results
        self.current = frame(0)
        self.actions: list[tuple[GameAction, dict[str, int] | None]] = []
        self.observation_space = self.current
        self.info = SimpleNamespace(game_id="test-game")
        self.scorecard_id = "scorecard-2"

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


def parent_session(tmp_path: Path) -> Session:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="session-001",
        game_id="test-game",
        model="test:model",
    )
    session.timeline.initialize(observation(0))
    session.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(1),
        model_revision="revision-1",
        prediction=None,
    )
    session.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(2),
        model_revision="revision-2",
        prediction=None,
    )
    return session


def commit_args() -> dict[str, object]:
    return {
        "actions": [{"action": "ACTION1"}],
        "reason": "Take one supported action.",
        "suggestion": "Inspect the result.",
    }


def test_restart_replays_exactly_without_mutating_session_evidence(
    tmp_path: Path,
) -> None:
    session = parent_session(tmp_path)
    timeline_before = session.timeline.path.read_bytes()
    messages_before = session.conversation.path.read_bytes()
    environment = FakeEnvironment([frame(1), frame(2)])
    adapter = ArcGameAdapter(environment)

    checkpoint = replay_session(
        session=session,
        adapter=adapter,
        initial_observation=adapter.reset(),
    )

    assert checkpoint == observation(2)
    assert environment.actions == [
        (GameAction.ACTION1, None),
        (GameAction.ACTION1, None),
    ]
    assert session.timeline.path.read_bytes() == timeline_before
    assert session.conversation.path.read_bytes() == messages_before
    assert session.path == tmp_path / "session-001"


def test_restart_fails_on_replay_divergence(tmp_path: Path) -> None:
    session = parent_session(tmp_path)
    adapter = ArcGameAdapter(FakeEnvironment([frame(9)]))

    with pytest.raises(ReplayDivergenceError, match="transition 0"):
        replay_session(
            session=session,
            adapter=adapter,
            initial_observation=adapter.reset(),
        )


def test_restart_refuses_an_uncertain_arc_action(tmp_path: Path) -> None:
    session = parent_session(tmp_path)
    session.events.append(
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
            session=session,
            adapter=adapter,
            initial_observation=adapter.reset(),
        )


def test_restart_detects_a_provider_valid_pending_deliberation(
    tmp_path: Path,
) -> None:
    session = parent_session(tmp_path)
    session.conversation.append([ModelRequest(parts=[])])
    session.events.append(
        turn=3,
        event=DeliberationStartedEvent(summary="pending deliberation"),
    )

    assert resumes_pending_deliberation(session) is True


def test_restarted_loop_continues_same_timeline_and_global_numbering(
    tmp_path: Path,
) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="session-001",
        game_id="test-game",
        model="test:model",
    )
    session.workspace.write_file(
        WriteFileQuery(path="world_model_v5.py", content=WORLD_MODEL)
    )

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[ToolCallPart("commit_actions", commit_args())]
        )

    first_environment = FakeEnvironment([frame(1)])
    first_adapter = ArcGameAdapter(first_environment)
    first = asyncio.run(
        run_agent_loop(
            agent=build_agent(FunctionModel(model)),
            adapter=first_adapter,
            initial_observation=first_adapter.reset(),
            session=session,
            policy=LoopPolicy(max_actions=1),
        )
    )
    assert first.actions == 1

    restarted_environment = FakeEnvironment([frame(1), frame(2)])
    restarted_adapter = ArcGameAdapter(restarted_environment)
    checkpoint = replay_session(
        session=session,
        adapter=restarted_adapter,
        initial_observation=restarted_adapter.reset(),
    )
    session.events.append(
        turn=1,
        event=EnvironmentRestartedEvent(
            summary="environment replay completed",
            attempt=2,
            operation_mode="online",
            environment_guid="guid-2",
            scorecard_id="scorecard-2",
            replayed_transitions=1,
            checkpoint_state=checkpoint.state,
            checkpoint_levels_completed=checkpoint.levels_completed,
            resumes_pending_deliberation=False,
        ),
    )
    second = asyncio.run(
        run_agent_loop(
            agent=build_agent(FunctionModel(model)),
            adapter=restarted_adapter,
            initial_observation=checkpoint,
            session=session,
            policy=LoopPolicy(max_actions=1),
            restart=LoopRestartContext(
                environment_attempt=2,
                replayed_transitions=1,
                resumes_pending_deliberation=False,
            ),
        )
    )

    assert second.actions == 1
    assert len(session.timeline.transitions()) == 2
    assert [
        entry.event.action_number
        for entry in session.events.entries()
        if entry.event.type == "action_completed"
    ] == [1, 2]
    assert [
        entry.turn
        for entry in session.events.entries()
        if entry.event.type == "turn_started"
    ] == [1, 2]


def test_restart_process_reopens_and_continues_the_same_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = parent_session(tmp_path)
    environment = FakeEnvironment([frame(1), frame(2)])
    captured: dict[str, object] = {}

    class FakeArcade:
        def __init__(self, **kwargs) -> None:
            captured["arcade_args"] = kwargs

        def make(self, game_id: str):
            assert game_id == "test-game"
            return environment

    async def record_loop(**kwargs):
        captured.update(kwargs)
        return LoopResult(
            stop_reason="max_turns",
            turns=0,
            actions=0,
            observation=kwargs["initial_observation"],
        )

    monkeypatch.setattr("beat_arc_agi_3.process.Arcade", FakeArcade)
    monkeypatch.setattr(
        "beat_arc_agi_3.process.build_openai_model", lambda settings: object()
    )
    monkeypatch.setattr(
        "beat_arc_agi_3.process.build_agent", lambda model: object()
    )
    monkeypatch.setattr("beat_arc_agi_3.process.run_agent_loop", record_loop)
    settings = SimpleNamespace(
        sessions_root=tmp_path,
        pydantic_ai_model="test:model",
        arc_api_key=SecretStr("arc-test"),
    )

    result = asyncio.run(
        restart_process(
            settings=settings,
            config=RestartProcessConfig(
                session_id="session-001",
                operation_mode=OperationMode.ONLINE,
            ),
        )
    )

    assert result.actions == 0
    continued = captured["session"]
    assert continued.path == session.path
    assert list(tmp_path.iterdir()) == [session.path]
    assert captured["restart"] == LoopRestartContext(
        environment_attempt=2,
        replayed_transitions=2,
        resumes_pending_deliberation=False,
    )
    assert [entry.event.type for entry in continued.events.entries()][-2:] == [
        "environment_replay_started",
        "environment_restarted",
    ]
