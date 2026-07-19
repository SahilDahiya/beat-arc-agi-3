import asyncio
from dataclasses import dataclass, field

import pytest
from arcengine import FrameData, GameState
from pydantic import SecretStr
from pydantic_ai import ModelMessage, ModelResponse, ToolCallPart, models
from pydantic_ai.models.function import AgentInfo, FunctionModel

from beat_arc_agi_3.agent import build_agent, build_openai_model
from beat_arc_agi_3.config import Settings
from beat_arc_agi_3.dependencies import AgentDeps, HistoryQuery
from beat_arc_agi_3.runner import deliberate, render_observation
from beat_arc_agi_3.schemas import CommitActions, GameObservation
from beat_arc_agi_3.workspace import ReadFileQuery


models.ALLOW_MODEL_REQUESTS = False


@dataclass
class RecordingHistory:
    calls: list[HistoryQuery] = field(default_factory=list)

    async def read(self, query: HistoryQuery) -> str:
        self.calls.append(query)
        return "#3 action=ACTION1; 4 cells changed"


@dataclass
class RecordingWorkspace:
    calls: list[ReadFileQuery] = field(default_factory=list)

    def read_file(self, query: ReadFileQuery) -> str:
        self.calls.append(query)
        return "notes.md (1 lines):\n1\tconfirmed"


@dataclass
class MemoryConversation:
    recorded: list[ModelMessage] = field(default_factory=list)

    def messages(self) -> tuple[ModelMessage, ...]:
        return tuple(self.recorded)

    def append(self, messages: list[ModelMessage]) -> None:
        self.recorded.extend(messages)


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
            }
        ],
        "reason": "Take the best supported probe.",
        "suggestion": "Inspect the resulting transition next turn.",
    }


def test_configured_model_uses_gpt_5_5_with_the_validated_api_key() -> None:
    settings = Settings(
        _env_file=None,
        arc_api_key=SecretStr("arc-test"),
        openai_api_key=SecretStr("openai-test"),
        pydantic_ai_model="openai:gpt-5.5",
        sessions_root="./sessions",
    )

    agent = build_agent(build_openai_model(settings))

    assert agent.model.model_name == "gpt-5.5"


def test_agent_fails_hard_when_model_is_missing() -> None:
    with pytest.raises(ValueError, match="model is required"):
        build_agent(None)


def test_agent_reads_history_then_returns_typed_commit() -> None:
    history = RecordingHistory()

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        assert [tool.name for tool in info.function_tools] == [
            "read_history",
            "read_file",
        ]
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

    deps = AgentDeps(
        observation=observation(1, 6),
        history=history,
        workspace=RecordingWorkspace(),
    )
    conversation = MemoryConversation()
    result = asyncio.run(
        deliberate(build_agent(FunctionModel(model)), deps, conversation)
    )

    assert isinstance(result, CommitActions)
    assert result.actions[0].action == "ACTION1"
    assert history.calls == [HistoryQuery(detail="brief", limit=3)]
    assert len(conversation.messages()) == 5


def test_successful_commit_skips_sibling_history_tool() -> None:
    history = RecordingHistory()

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[
                ToolCallPart("commit_actions", commit_args()),
                ToolCallPart("read_history", {"detail": "full", "limit": 1}),
            ]
        )

    deps = AgentDeps(
        observation=observation(1),
        history=history,
        workspace=RecordingWorkspace(),
    )
    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)), deps, MemoryConversation()
        )
    )

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

    deps = AgentDeps(
        observation=observation(1),
        history=RecordingHistory(),
        workspace=RecordingWorkspace(),
    )
    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)), deps, MemoryConversation()
        )
    )

    assert attempts == 2
    assert result.actions[0].action == "ACTION1"


def test_deliberation_reuses_session_message_history() -> None:
    message_counts: list[int] = []

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        message_counts.append(len(messages))
        return ModelResponse(parts=[ToolCallPart("commit_actions", commit_args())])

    agent = build_agent(FunctionModel(model))
    deps = AgentDeps(
        observation=observation(1),
        history=RecordingHistory(),
        workspace=RecordingWorkspace(),
    )
    conversation = MemoryConversation()

    asyncio.run(deliberate(agent, deps, conversation))
    asyncio.run(deliberate(agent, deps, conversation))

    assert message_counts == [1, 3]
    assert len(conversation.messages()) == 6


def test_agent_reads_a_workspace_file_then_commits() -> None:
    workspace = RecordingWorkspace()

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if len(messages) == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "read_file",
                        {"path": "notes.md", "offset": 2, "limit": 10},
                    )
                ]
            )
        return ModelResponse(parts=[ToolCallPart("commit_actions", commit_args())])

    deps = AgentDeps(
        observation=observation(1),
        history=RecordingHistory(),
        workspace=workspace,
    )
    result = asyncio.run(
        deliberate(build_agent(FunctionModel(model)), deps, MemoryConversation())
    )

    assert result.actions[0].action == "ACTION1"
    assert workspace.calls == [
        ReadFileQuery(path="notes.md", offset=2, limit=10)
    ]


def test_observation_renderer_is_compact_and_uses_hex_rows() -> None:
    rendered = render_observation(
        GameObservation.from_frame(
            FrameData(
                game_id="test-game",
                frame=[[[0, 10, 15], [1, 2, 3]]],
                state=GameState.NOT_FINISHED,
                levels_completed=2,
                win_levels=4,
                available_actions=[1, 6],
            )
        )
    )

    assert "State: NOT_FINISHED | level 2/4" in rendered
    assert "Legal actions: [1, 6]" in rendered
    assert "shape=2x3" in rendered
    assert "0af\n123" in rendered
    assert '"frame"' not in rendered
