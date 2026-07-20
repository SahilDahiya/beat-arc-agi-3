# Configuration direction

read_when: you are adding an agent option, loop policy, process bootstrap, session setting, or default value

Required resources never use fallbacks. `PYDANTIC_AI_MODEL`, `ARC_API_KEY`, and `SESSIONS_ROOT` must be present in `Settings`; a session must be explicitly created or opened; and process composition must pass the model into `build_agent`. The model setting must use `openai-codex:<model-name>`; other providers fail validation.

The harness owns its ChatGPT subscription OAuth flow. Run `uv run python -m beat_arc_agi_3 auth login` once, complete the browser authorization, and let the loopback callback return to `localhost:1455`. Credentials are stored outside the repository at `~/.beat-arc-agi-3/oauth.json`; its directory and file are restricted to modes `0700` and `0600`. Expired access tokens are refreshed and persisted before model construction. A missing, malformed, insecure, or unrefreshable credential store fails hard with no `OPENAI_API_KEY`, Codex CLI, model, or transport fallback.

For the current repository-local process, `.env` sets `SESSIONS_ROOT=./sessions`. `Settings` resolves it against the repository root and rejects paths outside or below that root. The runtime directory is ignored by Git.

Each process must receive an explicit Session selection and choose exactly one operation: create a fresh timestamped Session from a label, or replay-restart an existing Session by its exact ID. A Session stores `session.json`, `messages.jsonl`, `timeline.jsonl`, `events.jsonl`, canonical `notes.md`, the live `world_model_v5.py`, and cleared-level snapshots under `sessions/<session-id>/`. Environment history is generated from the Timeline; operational and decision history is reconstructed from the append-only event journal. Neither has a mutable duplicate.

The repository currently retains a small set of bounded policy defaults while process bootstrap is being built:

- History detail defaults to `brief`.
- History result limit defaults to `20` and is bounded to `1..100`.
- An empty-history summary currently reports `max_level=0`.
- Agent output/tool retry budget is `2`.
- Generated world-model calls default to a 10-second hard timeout.
- `run_python` defaults to 10 seconds and is bounded to `1..60`.
- `run_bfs` defaults to depth 24, 100,000 nodes, and 60 seconds; its hard bounds are depth 200, 4,000,000 nodes, and 600 seconds.

These values are useful starting policies, not permanent constants. During the configurable agent-and-loop work, move them into validated typed configuration and pass that configuration explicitly through process composition.

Pydantic AI usage enforcement is explicitly disabled for deliberation: request, tool-call, and token limits are all `None`. This also disables the SDK's implicit 50-request default. Model-request policy belongs to the harness and must not be introduced through `pydantic_ai.UsageLimits`. The harness has no per-deliberation request or tool-call bound.

Transient transport recovery is separate from Pydantic AI output/tool retry. The OpenAI client is configured with `max_retries=0`. `LoopPolicy.max_deliberation_retries` defaults to 3 and `retry_base_delay_seconds` defaults to 2.0, producing delays of 2, 4, and 8 seconds. Only classified transient OpenAI errors retry; every attempt is journaled and final exhaustion fails hard. CLI flags can change these harness-private diagnostics without revealing them to the agent.

`ProcessConfig` requires the game ID, session label, timezone-aware start time, and Arcade operation mode. `max_turns` and `max_actions` are optional positive values that default to `None`. It derives the storage ID as `<UTC timestamp>-<session label>`, using microsecond precision. `run_process` is the canonical composition root for a new Session. It resolves the real versioned game ID from Arcade before creating that Session. Missing or invalid required values fail before the model request and agent-driven action; environment creation failure and a missing initial observation fail without substitutes.

The `run` command creates a fresh Session from an explicit game and reusable label. The `restart --session SESSION_ID` command opens that exact Session, performs deterministic action replay, journals the new environment attempt, and continues in place only after exact agreement. Restart requires an operation mode but never creates another ID or directory. Omitted turn/action caps mean unlimited continuation of that process invocation. Restart is not exact live reconnection: each attempt's GUID and scorecard identity are persisted for diagnosis, but the ARC SDK does not expose restoration of the original affinity-bearing transport state.

## Loop policy boundary

The current optional diagnostic controls are:

- `max_turns`: maximum number of agent deliberations in one run.
- `max_actions`: maximum number of real environment actions in one run.
- `max_deliberation_retries`: transient retries after the first model attempt.
- `retry_base_delay_seconds`: base for exponential retry delay.

Both default to `None`, so production runs are unlimited. When supplied, they are independent ceilings: raising `max_actions` cannot extend a run that reaches `max_turns` first. They are harness-private diagnostics and never appear in `AgentDeps`, deliberation prompts, notes, or experiment context. The loop's Timeline-derived experiment evidence is always active and has no separate configuration.

Additional controls should be added only when their corresponding behavior is implemented. Likely future policy fields include:

- maximum actions accepted in one committed queue;
- maximum deaths or resets;
- an optional target number of completed levels;
- whether `GAME_OVER` allows another deliberation for `RESET`;
- whether level completion interrupts the remaining queue;
- generated-code and model-search resource bounds.

Configuration must not weaken the loop's safety invariants:

- `WIN` ends the run.
- The loop never exceeds a supplied turn or action cap.
- An action is checked against the environment's current legal actions immediately before execution.
- The remaining queue is discarded immediately when a world-model mismatch invalidates its assumptions.

The repeated construction of `LoopResult` for different stop reasons is an implementation detail, not policy. It may be consolidated behind a helper without changing configuration or behavior.

`end_strategy="early"` is a safety invariant rather than a tuning default: a successful `commit_actions` output ends deliberation and suppresses sibling function tools.

Target composition:

```text
Settings + AgentPolicy + LoopPolicy
                 |
        explicit process bootstrap
          |        |        |
        model    agent    Session
```

## Test side effects

The default `uv run pytest` invocation includes `paid_integration`. That test requires `ARC_API_KEY` plus a valid harness OAuth login, uses `PYDANTIC_AI_MODEL`, creates an online Arcade environment, makes a subscription-backed model request, and executes one real ARC action. The marker documents the test; it does not skip it. Unavailable credentials or services fail the suite by design.

Generated-code execution requires `bubblewrap` (`bwrap`). It is a required runtime dependency on the current Linux/WSL target; missing sandbox support fails model validation and analytical execution without an unsafe fallback.
