# Architecture

read_when: you are adding a module, tool, execution behavior, or dependency boundary

The canonical package is `beat_arc_agi_3` under `src/`.

```text
ARC environment creation/reset --> GameObservation
                              |
                         agent loop <--------------------+
                         /       \                       |
                    AgentDeps   CommitActions             |
                 /      |       \          |              |
        read_history file tools current  ArcAction queue   |
             |          |             one action at a time|
 TimelineHistoryReader  |                    |             |
             |      SessionWorkspace   ArcGameAdapter-step-+
             |                               |
             +--------- JsonlTimeline <------+
                      initial observation + action results

Session
├── session.json       immutable run metadata
├── messages.jsonl     Pydantic AI conversation batches
├── timeline.jsonl     authoritative environment evidence
└── other UTF-8 files  mutable session working material
```

Python owns all harness semantics. The current agent has four function tools: `read_history` for structured transition evidence plus trace-derived `read_file`, `write_file`, and `edit_file` operations for UTF-8 working material under the active Session. Each file tool has its own contract and implementation under `tools/`; `SessionWorkspace` owns only shared path confinement, file-presence checks, and atomic replacement. `commit_actions` is a structured output tool, not a normal function tool, so a valid commit terminates deliberation. Its output validator requires `world_model_v5.py` to exist in the active Session and checks every queued action against the current legal actions. The deliberation runner has no environment dependency: it persists the completed model-message batch and returns the validated queue. Only the outer loop owns the adapter that can execute ARC actions.

`Session` is the durable unit of one run. It owns immutable identity metadata, one game-bound `JsonlTimeline`, one append-only Pydantic AI conversation, and a `SessionWorkspace` rooted at `sessions/<session-id>/`. Session creation and opening are explicit; there is no default session or automatic resume. Workspace path resolution rejects traversal and symlinks that resolve beyond that root. Writes and successful edits replace files atomically; failed exact edits leave the prior file unchanged.

`JsonlTimeline` is a single-writer log. It validates the complete persisted sequence once when opened, retains the validated sequence in memory, and appends each new action result in O(1) without reparsing old grids. The initial observation is stored once; each later record stores only the executed action and resulting observation. Full before/after `Transition` values and terminal flags are derived in memory. `TimelineHistoryReader` formats only bounded evidence from that validated source.

The ARC adapter is a separate boundary. It translates a validated `ArcAction` into the toolkit's `GameAction`, passes click coordinates through the wrapper's separate `data` argument, and applies exactly one action when the loop asks it to.

`run_process` is the production composition root. It creates Arcade in the explicitly selected operation mode, requires the SDK's initial observation, creates a Session bound to the resolved versioned game ID, constructs the configured model and agent, and starts the bounded loop. ARC's environment wrappers reset eagerly during creation, so the loop receives that observation explicitly and does not issue a redundant reset.
