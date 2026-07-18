# Contracts

read_when: you are changing observations, actions, history access, agent dependencies, or deliberation output

- `GameObservation` is an immutable normalized snapshot of `arcengine.FrameData`.
- `ActionDecision` names one ARC action. Only `ACTION6` accepts `x` and `y`, both are required, and each coordinate is in `0..63`.
- `CommitActions` contains at least one action plus required `reason` and `suggestion` handoff text.
- Every action in `CommitActions` must be present in the current observation's `available_actions` before the value can leave deliberation.
- `HistoryQuery` accepts a detail level (`brief`, `full`, or `animation`) and a bounded result limit.
- `HistoryReader` is an async protocol returning textual history. Storage and formatting remain behind that interface.
- `AgentDeps` contains only the current observation and a `HistoryReader`. It contains no ARC environment and exposes no action-execution capability.
- Invalid structured output is retried through Pydantic AI validation. Exhausted retries fail; there is no fallback queue.
