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
11. Compose a complete real process from explicit settings and process configuration.
12. Exercise that composition in the default test suite with a paid model request and a real online ARC action.
13. Expose new-session process composition through `python -m beat_arc_agi_3 run` with explicit game, reusable session label, mode, and budget arguments; generated Session IDs are UTC timestamped.
14. Expose the trace-derived Schema Harness `read_file(path, offset=1, limit=2000)` tool over UTF-8 files confined to the active Session.
15. Give each Schema file tool a separate implementation and expose trace-derived `write_file(path, content)` plus exact `edit_file(path, old_string, new_string, replace_all=false)` with atomic persistence.
16. Require `world_model_v5.py` to implement the canonical stateful `init_state`, `predict`, and `is_goal` interfaces; invalid revisions never replace the live model.
17. Execute generated world-model code and ad hoc Python in a read-only, networkless Session sandbox with hard timeouts.
18. Expose trace-derived `run_backtest`, replay the complete Timeline, and require the exact current model revision and Timeline prefix to be green before commit.
19. Record a revision-bound prediction with every real action, compare it with reality, and cancel the committed queue at the first model mismatch.
20. Expose trace-derived `run_python` for bounded analysis and `run_bfs` for revision-bound model-space planning.

Competition submission integration, score reconstruction, candidate-model archives, and explicit process resume remain later milestones. The current loop deliberately requires a new empty Session.

The next implementation work moves the remaining agent/history defaults into typed configuration. See [Configuration direction](configuration.md) for those remaining policy values.
