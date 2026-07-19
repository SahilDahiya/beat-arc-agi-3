# Goal

read_when: you need to decide whether proposed work belongs in the current milestone

Build an ARC-AGI-3 agent harness incrementally in this repository. Schema Harness is evidence and inspiration, not a dependency or a codebase to clone.

The implemented foundation now provides:

1. Normalize ARC observations and actions into validated Python contracts.
2. Give a Pydantic AI agent read-only access to history.
3. Require the agent to terminate by returning a non-empty, typed action queue.
4. Validate every committed action against the current observation's legal actions.
5. Preserve Pydantic AI message history across turns in the active Session.
6. Execute committed queues one real action at a time, unlimited by default, with optional harness-private turn and action caps for diagnostics.
7. Drop the remaining queue when a level completes, the game enters `GAME_OVER`, or a later action becomes illegal.
8. Store each run as an explicit repository-local Session with immutable metadata.
9. Record the initial observation and each action result in that Session's append-only, game-bound JSONL Timeline.
10. Expose recent session evidence through brief, full, and animation history views.
11. Compose a complete real process from explicit settings and process configuration.
12. Exercise that composition in the default test suite with a subscription-backed model request and a real online ARC action.
13. Expose new-session process composition through `python -m beat_arc_agi_3 run` with explicit game, reusable session label, mode, and optional private cap arguments; generated Session IDs are UTC timestamped.
14. Expose the trace-derived Schema Harness `read_file(path, offset=1, limit=2000)` tool over UTF-8 files confined to the active Session.
15. Give each Schema file tool a separate implementation and expose trace-derived `write_file(path, content)` plus exact `edit_file(path, old_string, new_string, replace_all=false)` with atomic persistence.
16. Require `world_model_v5.py` to implement the canonical stateful `init_state`, `predict`, and `is_goal` interfaces; invalid revisions never replace the live model.
17. Execute generated world-model code and ad hoc Python in a read-only, networkless Session sandbox with hard timeouts.
18. Expose trace-derived `run_backtest`, replay the complete Timeline, and require the exact current model revision and Timeline prefix to be green before accepting a multi-action queue.
19. Use one prediction-guarded queue contract for planning and experimentation. A green model may carry a known prefix to an uncertain frontier action; an untrusted installed model permits exactly one unchecked action. Record revision-bound predictions when available and cancel the remaining queue at the first model mismatch.
20. Expose trace-derived `run_python` for bounded analysis and `run_bfs` for revision-bound model-space planning.
21. Persist a strict append-only `events.jsonl` journal with contiguous sequence numbers for session, turn, deliberation, tool, commit, action, mismatch, queue, and terminal run lifecycle evidence.
22. Derive compact experiment evidence from the Timeline before every deliberation: online prediction accuracy, recent mismatches and actions, actions without level progress, exact observable-state revisits, short cycles, nearest recent visual distance, and the latest counterexample.
23. Own ChatGPT subscription PKCE login, private credential persistence, and access-token refresh inside the harness, with explicit `openai-codex:` model selection and no API-key or subprocess fallback.
24. Seed every Session with canonical `notes.md`, include it once in the initial deliberation, retain its tool-mediated edits in conversation history, and direct the agent to maintain it as a pruned scientific scratchpad separating facts from hypotheses.
25. Atomically preserve the exact `world_model_v5.py` revision at every observed level completion in an immutable, journaled `snapshots/cleared_level_N.py` artifact.
26. Support exact-index, inclusive-range, action, terminal/reset, and prediction-status history selection. Every selected transition and earliest backtest mismatch includes deterministic connected-component boxes, color transitions and population deltas, geometric peripheral-band counts, and level-entry or prior-action references without assigning game-specific semantics.
27. Protect Session evidence extraction with a deterministic Pydantic Evals regression over the first two successful LS20 stage-zero Sessions plus synthetic negative and malformed fixtures, and score any newly produced Session against the same separate stage-outcome contract.
28. At the initial observation and after every observed level completion, inject a deterministic level-entry grounding protocol. It exposes only structural entry facts, requires facts and hypotheses to remain separate in `notes.md`, and makes the agent maintain a revisable temporary goal with an executable `is_goal` predicate, supporting evidence, falsifier, known unknowns, and cheapest discriminating probe.
29. Preserve raw ARC-advertised actions while deriving state-aware effective legality: `GAME_OVER` gives the agent an explicit RESET-only turn, RESET is journaled as a normal transition, and `WIN` remains terminal.
30. Record bounded BFS outcomes as typed canonical events and expose a deterministic per-level lifecycle report over action, prediction, synthesis, search, repair, queue, and terminal evidence.
31. Separate full-prefix replay trust from active-revision online evidence on the current level in every deliberation context.
32. Make synthesis mode explicit in the scientific scratchpad: use evidence-backed `goal_search` with an executable temporary predicate, or a bounded `discriminating_experiment` against a competing hypothesis.

JSON-over-stdio transport and human-readable event projections remain the next layer over this journal. Competition submission integration, score reconstruction, candidate-model archives, and explicit process resume remain later milestones. The current loop deliberately requires a new empty Session.

The next implementation work moves the remaining agent/history defaults into typed configuration. See [Configuration direction](configuration.md) for those remaining policy values.
