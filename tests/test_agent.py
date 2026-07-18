import asyncio
from dataclasses import dataclass, field

from arcengine import FrameData, GameState
from pydantic_ai import ModelMessage, ModelResponse, ToolCallPart, models
from pydantic_ai.models.function import AgentInfo, FunctionModel

from beat_arc_agi_3.agent import build_agent
from beat_arc_agi_3.dependencies import AgentDeps, HistoryQuery
from beat_arc_agi_3.runner import deliberate
from beat_arc_agi_3.schemas import CommitActions, GameObservation


models.ALLOW_MODEL_REQUESTS = False


@dataclass
class RecordingHistory:
    calls: list[HistoryQuery] = field(default_factory=list)

    async def read(self, query: HistoryQuery) -> str:
        self.calls.append(query)
        return "#3 action=ACTION1; 4 cells changed"


def observation(*available_actions: int) -> GameObservation:
    return GameObservation.from_frame(
        FrameData(
            game_id="test-game",
            frame=[[[0]]],
            state=GameState.NOT_FINISHED,
            available_actions=list(available_actions),
        )
    )


def commit_args(action: str = "ACTION1") -> dict[str, object]:
    return {
        "actions": [
            {
                "action": action,
                "reasoning": "Use the observed transition.",
                "confidence": 0.8,
            }
        ],
        "reason": "Take the best supported probe.",
        "suggestion": "Inspect the resulting transition next turn.",
    }


def test_agent_reads_history_then_returns_typed_commit() -> None:
    history = RecordingHistory()

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        assert [tool.name for tool in info.function_tools] == ["read_history"]
        assert [tool.name for tool in info.output_tools] == ["commit_actions"]
        if len(messages) == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "read_history", {"detail": "brief", "limit": 3}
                    )
                ]
            )
        return ModelResponse(parts=[ToolCallPart("commit_actions", commit_args())])

    deps = AgentDeps(observation=observation(1, 6), history=history)
    result = asyncio.run(deliberate(build_agent(FunctionModel(model)), deps))

    assert isinstance(result, CommitActions)
    assert result.actions[0].action == "ACTION1"
    assert history.calls == [HistoryQuery(detail="brief", limit=3)]


def test_successful_commit_skips_sibling_history_tool() -> None:
    history = RecordingHistory()

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[
                ToolCallPart("commit_actions", commit_args()),
                ToolCallPart("read_history", {"detail": "full", "limit": 1}),
            ]
        )

    deps = AgentDeps(observation=observation(1), history=history)
    result = asyncio.run(deliberate(build_agent(FunctionModel(model)), deps))

    assert result.actions[0].action == "ACTION1"
    assert history.calls == []


def test_agent_retries_a_commit_with_an_unavailable_action() -> None:
    attempts = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal attempts
        attempts += 1
        action = "ACTION2" if attempts == 1 else "ACTION1"
        return ModelResponse(
            parts=[ToolCallPart("commit_actions", commit_args(action))]
        )

    deps = AgentDeps(observation=observation(1), history=RecordingHistory())
    result = asyncio.run(deliberate(build_agent(FunctionModel(model)), deps))

    assert attempts == 2
    assert result.actions[0].action == "ACTION1"
