# Architecture

read_when: you are adding a module, tool, execution behavior, or dependency boundary

The canonical package is `beat_arc_agi_3` under `src/`.

Model access is an explicit composition boundary. `oauth_openai_codex.py` owns PKCE authorization and refresh, while `oauth_store.py` owns the private user-level credential file at `~/.beat-arc-agi-3/oauth.json`. `build_openai_model` injects those credentials into a dedicated client for the ChatGPT Codex backend. `OpenAICodexResponsesModel` adapts Pydantic AI's ordinary request entrypoint to the backend's required streaming Responses request and drains it into the same complete `ModelResponse` consumed by the loop. The agent and Session never receive refresh tokens, and no API-key, Codex subprocess, provider, endpoint, model, or non-streaming fallback exists.

```text
ARC environment creation/reset --> GameObservation
                              |
                         agent loop <--------------------------+
                         /       \                             |
                    AgentDeps   CommitActions                   |
                 /      |       \          |                    |
        read_history file tools synthesis  ArcAction queue     |
             |          |       tools      one action at a time|
 TimelineHistoryReader  |         |               |             |
             |   SessionWorkspace |     predict -> adapter-step |
             |              SynthesisHarness         |          |
             |              /       \                v          |
             |       backtest/BFS  model worker -> compare -----+
             |             |       (bubblewrap)
             +------ JsonlTimeline <------ action + prediction
                         |
                  EventJournal
            (ordered lifecycle evidence)

Session
├── session.json       immutable run metadata
├── messages.jsonl     Pydantic AI conversation batches
├── timeline.jsonl     environment evidence + pre-action predictions
├── events.jsonl       ordered lifecycle, tool, decision, and action evidence
├── world_model_v5.py canonical generated transition program
└── other UTF-8 files  mutable session working material
```

Python owns all harness semantics. The agent has seven function tools: `read_history`; trace-derived `read_file`, `write_file`, and `edit_file`; finite checker `run_backtest`; analytical workbench `run_python`; and model-space planner `run_bfs`. Each tool has its own contract and implementation under `tools/`. `commit_actions` remains a structured output tool, so a valid commit terminates deliberation. Its validator requires the exact current world-model revision and Timeline prefix to have a green backtest and checks every queued action against current legality.

`SynthesisHarness` owns model revision trust. `WorldModelRuntime` executes the canonical stateful generated interface through a JSON subprocess boundary. Both generated model execution and `run_python` use mandatory bubblewrap isolation: the Session is read-only, `/tmp` is private, the network namespace is absent, and execution has a hard timeout. A successful write or edit to `world_model_v5.py` validates prospective source before atomically replacing the live revision. Every revision starts untrusted until `run_backtest` reproduces all recorded transitions.

Only the outer loop owns the ARC adapter. Before each real action it obtains a prediction from the current green revision. It then executes exactly one action, appends the action, prediction, revision, and actual observation to the Timeline, and compares modeled with observed truth. An exact prediction advances trust to the longer Timeline prefix. A mismatch invalidates trust and drops the remaining queue.

Before each deliberation, the outer loop derives compact experiment evidence from the validated Timeline. It reports online prediction accuracy, the recent action/mismatch window, actions since level progress, exact observable-state revisits and short cycles, the nearest recent grid by changed-cell distance, and the latest counterexample. This is factual strategy pressure rather than another mutable memory source: the agent is told that a green replay establishes only finite consistency, to repair general mechanisms instead of transition-index epicycles, and to prefer the smallest discriminating experiment when no evidence-backed plan exists.

`Session` is the durable unit of one run. It owns immutable identity metadata, one game-bound `JsonlTimeline`, one append-only Pydantic AI conversation, and a `SessionWorkspace` rooted at `sessions/<session-id>/`. Session creation and opening are explicit; there is no default session or automatic resume. Workspace path resolution rejects traversal and symlinks that resolve beyond that root. Writes and successful edits replace files atomically; failed exact edits leave the prior file unchanged.

`EventJournal` is the canonical operational history for a Session. Each event is appended and fsynced with a contiguous one-based sequence, UTC timestamp, Session ID, turn number, and strict typed payload. Tool calls use Pydantic AI's actual `tool_call_id`; action-start events are durable before the irreversible ARC call, while action-completed events are written only after the corresponding Timeline transition. An `action_started` without `action_completed` therefore identifies an uncertain interrupted environment call. The journal stores compact meanings and pointers, not grids, generated source, or complete model messages. Future CLI and JSON-over-stdio views consume this backend-owned event meaning.

`JsonlTimeline` is a single-writer log. It validates the complete persisted sequence once when opened, retains the validated sequence in memory, and appends each new action result in O(1). The initial observation is stored once; each later record stores the executed action, pre-action model prediction and revision, and resulting observation. Full before/after `Transition` values, terminal flags, and `model_mispredicted` are derived and validated. `TimelineHistoryReader` formats only bounded evidence from that source.

The ARC adapter is a separate boundary. It translates a validated `ArcAction` into the toolkit's `GameAction`, passes click coordinates through the wrapper's separate `data` argument, and applies exactly one action when the loop asks it to.

`run_process` is the production composition root. It creates Arcade in the explicitly selected operation mode, requires the SDK's initial observation, creates a Session bound to the resolved versioned game ID, constructs the configured model and agent, and starts the bounded loop. ARC's environment wrappers reset eagerly during creation, so the loop receives that observation explicitly and does not issue a redundant reset.
