import asyncio
from dataclasses import dataclass, field

import pytest
from arcengine import FrameData, GameState
from pydantic import SecretStr
from pydantic_ai import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    UserPromptPart,
    models,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from beat_arc_agi_3.agent import INSTRUCTIONS, build_agent, build_openai_model
from beat_arc_agi_3.config import Settings
from beat_arc_agi_3.dependencies import AgentDeps, HistoryQuery
from beat_arc_agi_3.events import ArcEvent
from beat_arc_agi_3.oauth_store import OpenAICodexCredentials
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
from beat_arc_agi_3.world_model import WorldModelError


models.ALLOW_MODEL_REQUESTS = False


def test_agent_instructions_require_revisable_level_entry_grounding() -> None:
    instructions = " ".join(INSTRUCTIONS.split())

    assert "Level-entry grounding" in instructions
    assert "Observed facts" in instructions
    assert "Known unknowns" in instructions
    assert "Cheapest discriminating probe" in instructions
    assert "Temporary goal" in instructions
    assert "predicate, evidence, and falsifier" in instructions
    assert "re-run this protocol after every observed level_up" in instructions
    assert (
        "Do not treat is_goal returning False everywhere as final" in instructions
    )
    assert "Decision mode" in instructions
    assert "goal_search" in instructions
    assert "discriminating_experiment" in instructions
    assert "selected hypothesis" in instructions
    assert "competing hypothesis" in instructions
    assert "BFS EXHAUSTED" in instructions


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

    def read_text(self, path: str) -> str:
        assert path == "notes.md"
        return "# Notes\n\n## Confirmed mechanics\n- action 1 moves up\n"

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
    model_installed: bool = True
    backtest_calls: list[int] = field(default_factory=list)
    preflight_calls: list[tuple[str, ...]] = field(default_factory=list)
    inspect_calls: int = 0

    def inspect_model(self) -> str:
        self.inspect_calls += 1
        if not self.model_installed:
            raise WorldModelError("world_model_v5.py does not exist")
        return "test-revision"

    def model_revision(self) -> str:
        return "test-revision"

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


@dataclass
class RecordingEvents:
    recorded: list[tuple[int, ArcEvent]] = field(default_factory=list)

    def append(self, *, turn: int, event: ArcEvent) -> object:
        self.recorded.append((turn, event))
        return event


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
        "reason": "Take the best supported action.",
        "suggestion": "Inspect the resulting transition next turn.",
    }


def test_configured_model_uses_gpt_5_5_with_oauth_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "beat_arc_agi_3.agent.resolve_openai_codex_credentials",
        lambda: OpenAICodexCredentials(
            access="oauth-access",
            refresh="oauth-refresh",
            expires=1_760_000_000_000,
            account_id="acct-123",
        ),
    )
    settings = Settings(
        _env_file=None,
        arc_api_key=SecretStr("arc-test"),
        pydantic_ai_model="openai-codex:gpt-5.5",
        sessions_root="./sessions",
    )

    model = build_openai_model(settings)
    agent = build_agent(model)

    assert agent.model.model_name == "gpt-5.5"
    assert str(model._provider.base_url) == "https://chatgpt.com/backend-api/codex/"
    assert model._provider.client.default_headers["chatgpt-account-id"] == (
        "acct-123"
    )
    assert model._provider.client.default_headers["originator"] == (
        "beat-arc-agi-3"
    )
    assert model.settings == {"openai_store": False}


def test_agent_fails_hard_when_model_is_missing() -> None:
    with pytest.raises(ValueError, match="model is required"):
        build_agent(None)


def test_agent_reads_history_then_returns_typed_commit() -> None:
    history = RecordingHistory()
    events = RecordingEvents()

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
        assert set(schemas["read_history"]["properties"]) == {
            "detail",
            "limit",
            "indices",
            "start",
            "end",
            "action",
            "flags",
            "prediction_status",
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
        assert set(info.output_tools[0].parameters_json_schema["properties"]) == {
            "actions",
            "reason",
            "suggestion",
        }
        if len(messages) == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "read_history",
                        {
                            "detail": "brief",
                            "indices": [0, -1],
                            "action": 6,
                            "flags": "level_up",
                            "prediction_status": "exact",
                        },
                    )
                ]
            )
        return ModelResponse(parts=[ToolCallPart("commit_actions", commit_args())])

    deps = AgentDeps(
        observation=observation(1, 6),
        history=history,
        workspace=RecordingWorkspace(),
        synthesis=RecordingSynthesis(),
        events=events,
        turn=1,
    )
    conversation = MemoryConversation()
    result = asyncio.run(
        deliberate(build_agent(FunctionModel(model)), deps, conversation)
    )

    assert isinstance(result, CommitActions)
    assert result.actions[0].action == "ACTION1"
    assert history.calls == [
        HistoryQuery(
            detail="brief",
            indices=(0, -1),
            action=6,
            flags="level_up",
            prediction_status="exact",
        )
    ]
    assert deps.synthesis.preflight_calls == [("ACTION1",)]
    assert len(conversation.messages()) == 5
    assert [event.type for _, event in events.recorded] == [
        "deliberation_started",
        "tool_started",
        "tool_completed",
        "commit_accepted",
    ]


def test_agent_records_structured_bfs_outcome_before_tool_completion() -> None:
    events = RecordingEvents()
    calls = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "run_bfs",
                        {
                            "target": "level_up",
                            "max_depth": 8,
                            "node_budget": 100,
                        },
                    )
                ]
            )
        return ModelResponse(parts=[ToolCallPart("commit_actions", commit_args())])

    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)),
            AgentDeps(
                observation=observation(1),
                history=RecordingHistory(),
                workspace=RecordingWorkspace(),
                synthesis=RecordingSynthesis(),
                events=events,
                turn=1,
            ),
            MemoryConversation(),
        )
    )

    assert result.actions[0].action == "ACTION1"
    event_types = [event.type for _, event in events.recorded]
    assert event_types == [
        "deliberation_started",
        "tool_started",
        "bfs_completed",
        "tool_completed",
        "commit_accepted",
    ]
    bfs = events.recorded[2][1]
    assert bfs.target == "level_up"
    assert bfs.status == "found"
    assert bfs.max_depth == 8
    assert bfs.node_budget == 100
    assert all(turn == 1 for turn, _ in events.recorded)


def test_deliberation_has_no_pydantic_ai_request_or_tool_call_limit() -> None:
    model_calls = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal model_calls
        model_calls += 1
        if model_calls <= 51:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "read_history",
                        {"detail": "brief", "limit": 1},
                    )
                ]
            )
        return ModelResponse(parts=[ToolCallPart("commit_actions", commit_args())])

    deps = AgentDeps(
        observation=observation(1),
        history=RecordingHistory(),
        workspace=RecordingWorkspace(),
        synthesis=RecordingSynthesis(),
        events=RecordingEvents(),
        turn=1,
    )

    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)),
            deps,
            MemoryConversation(),
        )
    )

    assert model_calls == 52
    assert result.actions[0].action == "ACTION1"


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
        events=RecordingEvents(),
        turn=1,
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
        events=RecordingEvents(),
        turn=1,
    )
    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)), deps, MemoryConversation()
        )
    )

    assert attempts == 2
    assert result.actions[0].action == "ACTION1"


def test_agent_accepts_only_reset_after_game_over() -> None:
    attempts = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal attempts
        attempts += 1
        action = "ACTION1" if attempts == 1 else "RESET"
        return ModelResponse(
            parts=[ToolCallPart("commit_actions", commit_args(action))]
        )

    deps = AgentDeps(
        observation=GameObservation.from_frame(
            FrameData(
                game_id="test-game",
                frame=[[[0]]],
                state=GameState.GAME_OVER,
                available_actions=[1, 2, 3, 4],
            )
        ),
        history=RecordingHistory(),
        workspace=RecordingWorkspace(),
        synthesis=RecordingSynthesis(),
        events=RecordingEvents(),
        turn=1,
    )

    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)), deps, MemoryConversation()
        )
    )

    assert attempts == 2
    assert result.actions[0].action == "RESET"


def test_agent_must_create_world_model_before_committing() -> None:
    workspace = RecordingWorkspace(existing_files=set())
    synthesis = RecordingSynthesis(green=False, model_installed=False)
    model_calls = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal model_calls
        model_calls += 1
        if model_calls == 1:
            return ModelResponse(
                parts=[ToolCallPart("commit_actions", commit_args())]
            )
        if model_calls == 2:
            synthesis.model_installed = True
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
        return ModelResponse(parts=[ToolCallPart("commit_actions", commit_args())])

    deps = AgentDeps(
        observation=observation(1),
        history=RecordingHistory(),
        workspace=workspace,
        synthesis=synthesis,
        events=RecordingEvents(),
        turn=1,
    )
    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)), deps, MemoryConversation()
        )
    )

    assert model_calls == 3
    assert result.actions[0].action == "ACTION1"
    assert workspace.write_calls == [
        WriteFileQuery(
            path="world_model_v5.py",
            content="def predict(state, action):\n    return state\n",
        )
    ]
    assert synthesis.backtest_calls == []


def test_agent_accepts_one_unchecked_action_with_an_installed_untrusted_model() -> None:
    synthesis = RecordingSynthesis(green=False)

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "commit_actions",
                    commit_args(),
                )
            ]
        )

    deps = AgentDeps(
        observation=observation(1),
        history=RecordingHistory(),
        workspace=RecordingWorkspace(),
        synthesis=synthesis,
        events=RecordingEvents(),
        turn=1,
    )

    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)), deps, MemoryConversation()
        )
    )

    assert len(result.actions) == 1
    assert synthesis.inspect_calls == 1
    assert synthesis.preflight_calls == []


def test_agent_retries_an_untrusted_multi_action_queue_as_one_action() -> None:
    synthesis = RecordingSynthesis(green=False)
    attempts = 0

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal attempts
        attempts += 1
        actions = (
            [{"action": "ACTION1"}, {"action": "ACTION1"}]
            if attempts == 1
            else [{"action": "ACTION1"}]
        )
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "commit_actions",
                    {
                        "actions": actions,
                        "reason": "Reach and test the uncertain frontier.",
                        "suggestion": "Inspect the resulting transition.",
                    },
                )
            ]
        )

    deps = AgentDeps(
        observation=observation(1),
        history=RecordingHistory(),
        workspace=RecordingWorkspace(),
        synthesis=synthesis,
        events=RecordingEvents(),
        turn=1,
    )

    result = asyncio.run(
        deliberate(
            build_agent(FunctionModel(model)), deps, MemoryConversation()
        )
    )

    assert attempts == 2
    assert len(result.actions) == 1
    assert synthesis.inspect_calls == 2
    assert synthesis.preflight_calls == []


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
        events=RecordingEvents(),
        turn=1,
    )
    conversation = MemoryConversation()

    asyncio.run(deliberate(agent, deps, conversation))
    asyncio.run(deliberate(agent, deps, conversation))

    assert message_counts == [1, 3]
    assert len(conversation.messages()) == 6


def test_deliberation_seeds_notes_once_and_reuses_conversation_history() -> None:
    prompts: list[str] = []

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        request = messages[-1]
        assert isinstance(request, ModelRequest)
        prompt = request.parts[-1]
        assert isinstance(prompt, UserPromptPart)
        prompts.append(prompt.content)
        return ModelResponse(parts=[ToolCallPart("commit_actions", commit_args())])

    deps = AgentDeps(
        observation=observation(1),
        history=RecordingHistory(),
        workspace=RecordingWorkspace(),
        synthesis=RecordingSynthesis(),
        events=RecordingEvents(),
        turn=1,
    )

    agent = build_agent(FunctionModel(model))
    conversation = MemoryConversation()

    asyncio.run(deliberate(agent, deps, conversation))
    asyncio.run(deliberate(agent, deps, conversation))

    assert len(prompts) == 2
    assert "Your notes (notes.md; initial session checkpoint):" in prompts[0]
    assert "## Confirmed mechanics\n- action 1 moves up" in prompts[0]
    assert "Your notes (notes.md; initial session checkpoint):" not in prompts[1]
    assert "## Confirmed mechanics\n- action 1 moves up" not in prompts[1]


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
        events=RecordingEvents(),
        turn=1,
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
        events=RecordingEvents(),
        turn=1,
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
    assert "Legal actions: ACTION1, ACTION6" in rendered
    assert "shape=2x3" in rendered
    assert "0af\n123" in rendered
    assert '"frame"' not in rendered


def test_observation_renderer_exposes_effective_game_over_legality() -> None:
    rendered = render_observation(
        GameObservation.from_frame(
            FrameData(
                game_id="test-game",
                frame=[[[0]]],
                state=GameState.GAME_OVER,
                available_actions=[1, 2, 3, 4],
            )
        )
    )

    assert "Legal actions: RESET" in rendered
    assert "ARC-advertised actions: ACTION1, ACTION2, ACTION3, ACTION4" in rendered
