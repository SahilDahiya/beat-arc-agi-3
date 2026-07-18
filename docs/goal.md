# Goal

read_when: you need to decide whether proposed work belongs in the current milestone

Build an ARC-AGI-3 agent harness incrementally in this repository. Schema Harness is evidence and inspiration, not a dependency or a codebase to clone.

The implemented foundation now provides:

1. Normalize ARC observations and actions into validated Python contracts.
2. Give a Pydantic AI agent read-only access to history.
3. Require the agent to terminate by returning a non-empty, typed action queue.
4. Validate every committed action against the current observation's legal actions.
5. Preserve Pydantic AI message history across turns in the active Session.
6. Execute committed queues one real action at a time under explicit turn and action limits.
7. Drop the remaining queue when a level completes, the game enters `GAME_OVER`, or a later action becomes illegal.
8. Store each run as an explicit repository-local Session with immutable metadata.
9. Record the initial observation and each action result in that Session's append-only, game-bound JSONL Timeline.
10. Expose recent session evidence through brief, full, and animation history views.

World-model editing, backtesting, search, model-misprediction queue cancellation, process bootstrap, and competition submission integration remain later milestones. Resuming an environment process from an existing Session is also not implemented; the current loop deliberately requires a new empty Session.

The next implementation work adds process bootstrap and moves the remaining agent/history defaults into typed configuration. See [Configuration direction](configuration.md) for those remaining policy values.
