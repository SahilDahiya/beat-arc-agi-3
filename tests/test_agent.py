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
from beat_arc_agi_3.synthesis import (
    BacktestReport,
    BacktestRequiredError,
    BacktestTrust,
    BfsReport,
)
from beat_arc_agi_3.tools.edit_file import EditFileQuery
from beat_arc_agi_3.tools.read_file import ReadFileQuery
from beat_arc_agi_3.tools.write_file import WriteFileQuery


models.ALLOW_MODEL_REQUESTS = False


@dataclass
class RecordingHistory:
    calls: list[HistoryQuery] = field(default_factory=list)

    async def read(self, query: HistoryQuery) -> str:
        self.calls.append(query)
        return "#3 action=ACTION1; 4 cells changed"


@dataclass
class RecordingWorkspace:
    read_calls: list[ReadFileQuery] = field(default_factory=list)
    write_calls: list[WriteFileQuery] = field(default_factory=list)
    edit_calls: list[EditFileQuery] = field(default_factory=list)
    existing_files: set[str] = field(
        default_factory=lambda: {"world_model_v5.py"}
    )

    def has_file(self, path: str) -> bool:
        return path in self.existing_files

    def read_file(self, query: ReadFileQuery) -> str:
        self.read_calls.append(query)
        return "notes.md (1 lines):\n1\tconfirmed"

    def write_file(self, query: WriteFileQuery) -> str:
        self.write_calls.append(query)
        self.existing_files.add(query.path)
        return f"OK: wrote {len(query.content)} bytes to {query.path}."

    def edit_file(self, query: EditFileQuery) -> str:
        self.edit_calls.append(query)
        return f"OK: replaced 1 occurrence(s) in {query.path}."


@dataclass
class RecordingSynthesis:
    green: bool = True
    backtest_calls: list[int] = field(default_factory=list)
    preflight_calls: list[tuple[str, ...]] = field(default_factory=list)

    def run_backtest(self, *, max_details: int = 1) -> BacktestReport:
        self.backtest_calls.append(max_details)
        self.green = True
        return BacktestReport(
            revision="test-revision",
            timeline_transitions=0,
            transitions_checked=0,
            exact_transitions=0,
            status="green",
        )

    def require_green(self) -> BacktestTrust:
        if not self.green:
            raise BacktestRequiredError(
                "current world model revision has not been backtested"
            )
        return BacktestTrust(
            revision="test-revision",
            timeline_transitions=0,
            state={},
            grid=((0,),),
        )

    def run_bfs(
        self,
        *,
        target: str,
        max_depth: int,
        node_budget: int,
        click_candidates: tuple[tuple[int, int], ...],
        timeout_seconds: int,
    ) -> BfsReport:
        self.require_green()
        return BfsReport(
            revision="test-revision",
            target=target,
            status="found",
            actions=(),
            predicted_grid=((0,),),
            expanded_nodes=0,
            distinct_states=1,
            depth=0,
        )

    def preflight_actions(self, actions) -> None:
        self.require_green()
        self.preflight_calls.append(tuple(action.action for action in actions))


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
            "write_file",
            "edit_file",
            "run_backtest",
            "run_python",
            "run_bfs",
        ]
        schemas = {
            tool.name: tool.parameters_json_schema
            for tool in info.function_tools
        }
        assert set(schemas["write_file"]["properties"]) == {
            "path",
            "content",
        }
        assert set(schemas["edit_file"]["properties"]) == {
            "path",
            "old_string",
            "new_string",
            "replace_all",
        }
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
        synthesis=RecordingSynthesis(),
    )
    conversation = MemoryConversation()
    result = asyncio.run(
        deliberate(build_agent(FunctionModel(model)), deps, conversation)
    )

    assert isinstance(result, CommitActions)
    assert result.actions[0].action == "ACTION1"
    assert history.calls == [HistoryQuery(detail="brief", limit=3)]
    assert deps.synthesis.preflight_calls == [("ACTION1",)]
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
        synthesis=RecordingSynthesis(),
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
        synthesis=RecordingSynthesis(),
    )
    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)), deps, MemoryConversation()
        )
    )

    assert attempts == 2
    assert result.actions[0].action == "ACTION1"


def test_agent_must_create_and_backtest_world_model_before_committing() -> None:
    workspace = RecordingWorkspace(existing_files=set())
    synthesis = RecordingSynthesis(green=False)
    model_calls = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal model_calls
        model_calls += 1
        if model_calls == 1:
            return ModelResponse(
                parts=[ToolCallPart("commit_actions", commit_args())]
            )
        if model_calls == 2:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "write_file",
                        {
                            "path": "world_model_v5.py",
                            "content": "def predict(state, action):\n    return state\n",
                        },
                    )
                ]
            )
        if model_calls == 3:
            return ModelResponse(
                parts=[ToolCallPart("run_backtest", {"max_details": 2})]
            )
        return ModelResponse(parts=[ToolCallPart("commit_actions", commit_args())])

    deps = AgentDeps(
        observation=observation(1),
        history=RecordingHistory(),
        workspace=workspace,
        synthesis=synthesis,
    )
    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)), deps, MemoryConversation()
        )
    )

    assert model_calls == 4
    assert result.actions[0].action == "ACTION1"
    assert workspace.write_calls == [
        WriteFileQuery(
            path="world_model_v5.py",
            content="def predict(state, action):\n    return state\n",
        )
    ]
    assert synthesis.backtest_calls == [2]


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
        synthesis=RecordingSynthesis(),
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
        synthesis=RecordingSynthesis(),
    )
    result = asyncio.run(
        deliberate(build_agent(FunctionModel(model)), deps, MemoryConversation())
    )

    assert result.actions[0].action == "ACTION1"
    assert workspace.read_calls == [
        ReadFileQuery(path="notes.md", offset=2, limit=10)
    ]


def test_agent_writes_then_edits_workspace_files_before_commit() -> None:
    workspace = RecordingWorkspace()
    model_calls = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal model_calls
        model_calls += 1
        if model_calls == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "write_file",
                        {"path": "notes.md", "content": "hypothesis"},
                    )
                ]
            )
        if model_calls == 2:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "edit_file",
                        {
                            "path": "notes.md",
                            "old_string": "hypothesis",
                            "new_string": "confirmed",
                            "replace_all": False,
                        },
                    )
                ]
            )
        return ModelResponse(parts=[ToolCallPart("commit_actions", commit_args())])

    deps = AgentDeps(
        observation=observation(1),
        history=RecordingHistory(),
        workspace=workspace,
        synthesis=RecordingSynthesis(),
    )
    result = asyncio.run(
        deliberate(build_agent(FunctionModel(model)), deps, MemoryConversation())
    )

    assert result.actions[0].action == "ACTION1"
    assert workspace.write_calls == [
        WriteFileQuery(path="notes.md", content="hypothesis")
    ]
    assert workspace.edit_calls == [
        EditFileQuery(
            path="notes.md",
            old_string="hypothesis",
            new_string="confirmed",
            replace_all=False,
        )
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
