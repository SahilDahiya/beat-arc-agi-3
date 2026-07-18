# Architecture

read_when: you are adding a module, tool, execution behavior, or dependency boundary

The canonical package is `beat_arc_agi_3` under `src/`.

```text
ARC FrameData -> GameObservation -> AgentDeps
                                      |
                         Pydantic AI deliberation
                           |                  |
                    read_history       commit_actions
                           |                  |
                    HistoryReader       CommitActions
                                              |
                                      returned, not run
```

Python owns all harness semantics. The current agent has one read-only function tool, `read_history`. `commit_actions` is a structured output tool, not a normal function tool, so a valid commit terminates deliberation. The runner returns that validated value and has no environment dependency; it therefore cannot execute an ARC action accidentally.

The ARC adapter is a separate boundary. It translates a validated `ActionDecision` into the toolkit's `GameAction` and applies exactly one action when an explicit caller asks it to.
