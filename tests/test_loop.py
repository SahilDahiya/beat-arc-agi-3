import asyncio
from pathlib import Path

from arcengine import FrameData, GameAction, GameState
from pydantic_ai import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.agent import build_agent
from beat_arc_agi_3.loop import LoopPolicy, run_agent_loop
from beat_arc_agi_3.session import Session


def frame(
    value: int,
    *,
    state: GameState = GameState.NOT_FINISHED,
    levels_completed: int = 0,
    available_actions: list[int] | None = None,
) -> FrameData:
    return FrameData(
        game_id="test-game",
        frame=[[[value]]],
        state=state,
        levels_completed=levels_completed,
        win_levels=2,
        available_actions=available_actions or [1],
    )


class FakeEnvironment:
    def __init__(self, results: list[FrameData]) -> None:
        self.results = results
        self.current = frame(0)
        self.actions: list[tuple[GameAction, dict[str, int] | None]] = []
        self.reset_calls = 0

    @property
    def action_space(self) -> list[GameAction]:
        return [
            GameAction.from_id(action_id)
            for action_id in self.current.available_actions
        ]

    def reset(self) -> FrameData:
        self.reset_calls += 1
        return self.current

    def step(
        self, action: GameAction, data: dict[str, int] | None = None
    ) -> FrameData:
        self.actions.append((action, data))
        self.current = self.results.pop(0)
        return self.current


def commit(actions: list[dict[str, object]]) -> dict[str, object]:
    return {
        "actions": actions,
        "reason": "Execute the shortest supported plan.",
        "suggestion": "Inspect the resulting transition.",
    }


def create_session(tmp_path: Path) -> Session:
    return Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="test:model",
    )


def test_loop_drops_queue_suffix_on_level_up_and_reasons_again(
    tmp_path: Path,
) -> None:
    environment = FakeEnvironment(
        [
            frame(1, levels_completed=1),
            frame(2, state=GameState.WIN, levels_completed=2),
        ]
    )
    calls = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        actions = (
            [{"action": "ACTION1"}, {"action": "ACTION1"}]
            if calls == 1
            else [{"action": "ACTION1"}]
        )
        return ModelResponse(
            parts=[ToolCallPart("commit_actions", commit(actions))]
        )

    session = create_session(tmp_path)
    adapter = ArcGameAdapter(environment)
    result = asyncio.run(
        run_agent_loop(
            agent=build_agent(FunctionModel(model)),
            adapter=adapter,
            initial_observation=adapter.reset(),
            session=session,
            policy=LoopPolicy(max_turns=5, max_actions=5),
        )
    )

    assert result.stop_reason == "win"
    assert result.turns == 2
    assert result.actions == 2
    assert environment.reset_calls == 1
    assert environment.actions == [
        (GameAction.ACTION1, None),
        (GameAction.ACTION1, None),
    ]
    assert len(session.timeline.transitions()) == 2
    assert len(session.conversation.messages()) == 6


def test_loop_honors_the_total_action_limit(tmp_path: Path) -> None:
    environment = FakeEnvironment([frame(1), frame(2)])

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "commit_actions",
                    commit(
                        [
                            {"action": "ACTION1"},
                            {"action": "ACTION1"},
                        ]
                    ),
                )
            ]
        )

    adapter = ArcGameAdapter(environment)
    result = asyncio.run(
        run_agent_loop(
            agent=build_agent(FunctionModel(model)),
            adapter=adapter,
            initial_observation=adapter.reset(),
            session=create_session(tmp_path),
            policy=LoopPolicy(max_turns=5, max_actions=1),
        )
    )

    assert result.stop_reason == "max_actions"
    assert result.actions == 1
    assert len(environment.actions) == 1
