# Configuration direction

read_when: you are adding an agent option, loop policy, process bootstrap, session setting, or default value

Required resources never use fallbacks. Model selection, API keys, and `SESSIONS_ROOT` must be present in `Settings`; a session must be explicitly created or opened; and process composition must pass the model into `build_agent`.

For the current repository-local process, `.env` sets `SESSIONS_ROOT=./sessions`. `Settings` resolves it against the repository root and rejects paths outside or below that root. The runtime directory is ignored by Git.

Each process must receive an explicit session ID and choose exactly one operation: create a new session or open an existing one. A session stores `session.json`, `messages.jsonl`, and `timeline.jsonl` under `sessions/<session-id>/`. History is generated from that session Timeline and is not persisted as a second source of truth. The current execution loop accepts only a newly created empty Session; process-level environment resume remains later work.

The repository currently retains a small set of bounded policy defaults while process bootstrap is being built:

- History detail defaults to `brief`.
- History result limit defaults to `20` and is bounded to `1..100`.
- An empty-history summary currently reports `max_level=0`.
- Agent output/tool retry budget is `2`.
- Deliberation request limit is `8`.
- Deliberation tool-call limit is `8`.

These values are useful starting policies, not permanent constants. During the configurable agent-and-loop work, move them into validated typed configuration and pass that configuration explicitly through process composition.

`LoopPolicy` now requires explicit maximum turn and action counts. Process configuration still needs game selection, create-versus-open mode, and process bootstrap. Missing required process values must fail before a model request or environment action.

## Loop policy boundary

The current configurable loop controls are:

- `max_turns`: maximum number of agent deliberations in one run.
- `max_actions`: maximum number of real environment actions in one run.

Additional controls should be added only when their corresponding behavior is implemented. Likely future policy fields include:

- maximum actions accepted in one committed queue;
- maximum deaths or resets;
- an optional target number of completed levels;
- whether `GAME_OVER` allows another deliberation for `RESET`;
- whether level completion interrupts the remaining queue;
- model-misprediction handling and retry bounds.

Configuration must not weaken the loop's safety invariants:

- `WIN` ends the run.
- The loop never exceeds its explicit turn or action budgets.
- An action is checked against the environment's current legal actions immediately before execution.
- The remaining queue is discarded when a world-model mismatch invalidates its assumptions, once model checking exists.

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
