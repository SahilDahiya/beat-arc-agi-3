import asyncio
from pathlib import Path

from arcengine import FrameData, GameAction, GameState
from pydantic_ai import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.agent import build_agent
from beat_arc_agi_3.loop import LoopPolicy, run_agent_loop
from beat_arc_agi_3.session import Session
from beat_arc_agi_3.tools.write_file import WriteFileQuery


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


def create_session(tmp_path: Path, *, world_model: str) -> Session:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="run-001",
        game_id="test-game",
        model="test:model",
    )
    session.workspace.write_file(
        WriteFileQuery(
            path="world_model_v5.py",
            content=world_model,
        )
    )
    return session


def test_loop_drops_queue_suffix_on_level_up_and_reasons_again(
    tmp_path: Path,
) -> None:
    environment = FakeEnvironment(
        [
            frame(1, levels_completed=1),
            frame(2, state=GameState.WIN, levels_completed=2),
        ]
    )
    model_calls = 0
    commits = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal model_calls, commits
        model_calls += 1
        if model_calls % 2 == 1:
            return ModelResponse(
                parts=[ToolCallPart("run_backtest", {"max_details": 1})]
            )
        commits += 1
        actions = (
            [{"action": "ACTION1"}, {"action": "ACTION1"}]
            if commits == 1
            else [{"action": "ACTION1"}]
        )
        return ModelResponse(
            parts=[ToolCallPart("commit_actions", commit(actions))]
        )

    session = create_session(
        tmp_path,
        world_model=(
            "def init_state(entry_grid):\n"
            "    return {\"steps\": 0}\n\n"
            "def predict(state, grid, action, x=None, y=None):\n"
            "    value = grid[0][0] + 1\n"
            "    steps = state[\"steps\"] + 1\n"
            "    flags = {\"level_up\": True, \"dead\": False, "
            "\"win\": steps >= 2}\n"
            "    return [[value]], flags, {\"steps\": steps}\n\n"
            "def is_goal(state, grid):\n"
            "    return state[\"steps\"] >= 2\n"
        ),
    )
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
    assert len(session.conversation.messages()) == 10


def test_loop_honors_the_total_action_limit(tmp_path: Path) -> None:
    environment = FakeEnvironment([frame(1), frame(2)])

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if len(messages) == 1:
            return ModelResponse(
                parts=[ToolCallPart("run_backtest", {"max_details": 1})]
            )
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
            session=create_session(
                tmp_path,
                world_model=(
                    "def init_state(entry_grid):\n"
                    "    return {}\n\n"
                    "def predict(state, grid, action, x=None, y=None):\n"
                    "    return [[grid[0][0] + 1]], "
                    "{\"level_up\": False, \"dead\": False, "
                    "\"win\": False}, state\n\n"
                    "def is_goal(state, grid):\n"
                    "    return False\n"
                ),
            ),
            policy=LoopPolicy(max_turns=5, max_actions=1),
        )
    )

    assert result.stop_reason == "max_actions"
    assert result.actions == 1
    assert len(environment.actions) == 1


def test_loop_cancels_queue_suffix_after_model_misprediction(
    tmp_path: Path,
) -> None:
    environment = FakeEnvironment([frame(9), frame(10)])

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if len(messages) == 1:
            return ModelResponse(
                parts=[ToolCallPart("run_backtest", {"max_details": 1})]
            )
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
    session = create_session(
        tmp_path,
        world_model=(
            "def init_state(entry_grid):\n"
            "    return {}\n\n"
            "def predict(state, grid, action, x=None, y=None):\n"
            "    return [[grid[0][0] + 1]], "
            "{\"level_up\": False, \"dead\": False, "
            "\"win\": False}, state\n\n"
            "def is_goal(state, grid):\n"
            "    return False\n"
        ),
    )

    result = asyncio.run(
        run_agent_loop(
            agent=build_agent(FunctionModel(model)),
            adapter=adapter,
            initial_observation=adapter.reset(),
            session=session,
            policy=LoopPolicy(max_turns=1, max_actions=5),
        )
    )

    assert result.stop_reason == "max_turns"
    assert result.actions == 1
    assert len(environment.actions) == 1
    assert session.timeline.transitions()[0].model_mispredicted is True
