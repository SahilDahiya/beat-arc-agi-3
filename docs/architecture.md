# Architecture

read_when: you are adding a module, tool, execution behavior, or dependency boundary

The canonical package is `beat_arc_agi_3` under `src/`.

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

Session
├── session.json       immutable run metadata
├── messages.jsonl     Pydantic AI conversation batches
├── timeline.jsonl     environment evidence + pre-action predictions
├── world_model_v5.py canonical generated transition program
└── other UTF-8 files  mutable session working material
```

Python owns all harness semantics. The agent has seven function tools: `read_history`; trace-derived `read_file`, `write_file`, and `edit_file`; finite checker `run_backtest`; analytical workbench `run_python`; and model-space planner `run_bfs`. Each tool has its own contract and implementation under `tools/`. `commit_actions` remains a structured output tool, so a valid commit terminates deliberation. Its validator requires the exact current world-model revision and Timeline prefix to have a green backtest and checks every queued action against current legality.

`SynthesisHarness` owns model revision trust. `WorldModelRuntime` executes the canonical stateful generated interface through a JSON subprocess boundary. Both generated model execution and `run_python` use mandatory bubblewrap isolation: the Session is read-only, `/tmp` is private, the network namespace is absent, and execution has a hard timeout. A successful write or edit to `world_model_v5.py` validates prospective source before atomically replacing the live revision. Every revision starts untrusted until `run_backtest` reproduces all recorded transitions.

Only the outer loop owns the ARC adapter. Before each real action it obtains a prediction from the current green revision. It then executes exactly one action, appends the action, prediction, revision, and actual observation to the Timeline, and compares modeled with observed truth. An exact prediction advances trust to the longer Timeline prefix. A mismatch invalidates trust and drops the remaining queue.

`Session` is the durable unit of one run. It owns immutable identity metadata, one game-bound `JsonlTimeline`, one append-only Pydantic AI conversation, and a `SessionWorkspace` rooted at `sessions/<session-id>/`. Session creation and opening are explicit; there is no default session or automatic resume. Workspace path resolution rejects traversal and symlinks that resolve beyond that root. Writes and successful edits replace files atomically; failed exact edits leave the prior file unchanged.

`JsonlTimeline` is a single-writer log. It validates the complete persisted sequence once when opened, retains the validated sequence in memory, and appends each new action result in O(1). The initial observation is stored once; each later record stores the executed action, pre-action model prediction and revision, and resulting observation. Full before/after `Transition` values, terminal flags, and `model_mispredicted` are derived and validated. `TimelineHistoryReader` formats only bounded evidence from that source.

The ARC adapter is a separate boundary. It translates a validated `ArcAction` into the toolkit's `GameAction`, passes click coordinates through the wrapper's separate `data` argument, and applies exactly one action when the loop asks it to.

`run_process` is the production composition root. It creates Arcade in the explicitly selected operation mode, requires the SDK's initial observation, creates a Session bound to the resolved versioned game ID, constructs the configured model and agent, and starts the bounded loop. ARC's environment wrappers reset eagerly during creation, so the loop receives that observation explicitly and does not issue a redundant reset.
