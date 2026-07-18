# Goal

read_when: you need to decide whether proposed work belongs in the current milestone

Build an ARC-AGI-3 agent harness incrementally in this repository. Schema Harness is evidence and inspiration, not a dependency or a codebase to clone.

The current milestone is the smallest safe deliberation boundary:

1. Normalize ARC observations and actions into validated Python contracts.
2. Give a Pydantic AI agent read-only access to history.
3. Require the agent to terminate by returning a non-empty, typed action queue.
4. Validate every committed action against the current observation's legal actions.
5. Return the queue to the caller without executing it.

World-model editing, backtesting, search, timeline persistence, queue execution, misprediction handling, and competition submission integration are later milestones.
