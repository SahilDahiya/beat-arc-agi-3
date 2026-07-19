# Contracts

read_when: you are changing observations, actions, history access, agent dependencies, or deliberation output

- `GameObservation` is an immutable normalized snapshot of `arcengine.FrameData`. It stores the final `grid` separately from optional intermediate animation `ticks`.
- `ArcAction` is a pure environment command with no reasoning metadata. Only `ACTION6` accepts `x` and `y`, both are required, and each coordinate is in `0..63`.
- `CommitActions` contains at least one action plus required `reason` and `suggestion` handoff text.
- Every action in `CommitActions` must be present in the current observation's `available_actions` before the value can leave deliberation.
- `HistoryQuery` accepts a detail level (`brief`, `full`, or `animation`) and a bounded result limit.
- `ReadFileQuery` is the first trace-derived Schema Harness file-tool contract: required `path`, one-based `offset=1`, and `limit=2000`. No alternate argument names are accepted.
- `SessionWorkspace.read_file` reads UTF-8 text only beneath the active Session, numbers returned lines, reports partial ranges, and caps large responses at a complete-line boundary with a continuation offset. Missing files and paths escaping through traversal, absolute paths, or symlinks fail explicitly.
- `Transition` is a derived in-memory view containing its sequence index, before observation, executed action, after observation, and derived level-up/death/win flags.
- `SessionMetadata` records explicit session ID, game ID, model, and timezone-aware creation time in `session.json`.
- `Session.create` and `Session.open` require an explicit safe session ID. Creation fails if that session exists; opening fails if it is missing; unsafe path-like IDs are rejected.
- Every Session owns `sessions/<session-id>/timeline.jsonl`, `messages.jsonl`, and its rooted workspace capability. There is no global Timeline, conversation, workspace, or automatic resume.
- `JsonlTimeline` is append-only, game-bound, single-writer, and must be explicitly created. Its first record is the initial observation; each later record contains a contiguous index, executed action, and resulting observation. Opening validates the complete log once. Appending validates only the new record and never duplicates the previous observation.
- `JsonlConversation` stores each completed Pydantic AI message batch as one JSONL record. Deliberation passes all validated session messages back through `message_history` and persists the new batch before returning a queue for execution.
- `HistoryReader` is an async protocol returning textual history. `TimelineHistoryReader` is its canonical implementation and reads only validated Timeline records.
- Brief history reports action, changed-cell count, resulting state, level, and flags. Full history adds final before/after grids. Animation history includes intermediate ticks followed by the final resulting grid.
- `AgentDeps` contains the current observation, a `HistoryReader`, and a read-only `WorkspaceReader`. It contains no ARC environment and exposes no action-execution capability.
- `LoopPolicy` requires explicit positive `max_turns` and `max_actions` values. The loop requires a new empty Session plus the explicit initial observation produced during environment creation, and executes committed actions sequentially without resetting that environment again.
- A queue is interrupted after level completion, `GAME_OVER`, `WIN`, or a legality change. `WIN` ends the outer loop; `GAME_OVER` starts another deliberation so the agent may choose `RESET`.
- Turn and action budgets are policy values. Winning, checking legality immediately before execution, respecting those budgets, and eventually canceling a queue after model misprediction are safety invariants rather than optional tuning behavior.
- `build_agent` requires an explicit model instance. Configuration-to-provider construction is a separate `build_openai_model(Settings)` step; a missing model fails immediately.
- `ProcessConfig` explicitly supplies game ID, reusable session label, timezone-aware start time, Arcade operation mode, and positive turn/action bounds. Its derived Session ID is a UTC timestamp followed by the label. `run_process` is the only production composition path and fails if Arcade cannot create the environment or provide its eager initial observation.
- `Settings` requires API keys, `PYDANTIC_AI_MODEL`, and `SESSIONS_ROOT`. `.env` configures `openai:gpt-5.5` and repository-local `./sessions`; neither has a code fallback.
- Invalid structured output is retried through Pydantic AI validation. Exhausted retries fail; there is no fallback queue.
