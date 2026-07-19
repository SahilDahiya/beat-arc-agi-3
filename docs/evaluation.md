# Evaluation

read_when: you are adding an eval case, changing an eval metric, or scoring a new Session

The first evaluation is `ls20_session_evidence_regression_v1`. It validates
evidence extraction against the two repository-local Sessions that first
progressed from `levels_completed=0` to `levels_completed=1`:

- `20260719T070540.523307Z-ls20-world-model-001`
- `20260719T165557.195241Z-ls20-world-model-001`

Run it without a model request or an ARC environment action:

```bash
uv run python -m beat_arc_agi_3 eval ls20-session-evidence
```

These are success-selected historical fixtures. Their 2/2 result validates the
scorer and durable evidence contract; it does not estimate current agent
capability or establish a baseline success rate. The regression declares exact
expected facts for both Sessions, including actions, turns, prediction counts,
tool counts, snapshot evidence, and post-target failure state.

Synthetic tests cover target-not-reached, missing target-action evidence,
missing snapshot evidence, run failure before target, interruption before
target, and failure after target. Regression cases compare observed facts with
their declared expectation, so a correctly extracted failed Session passes and
an always-success scorer cannot pass the suite.

## What is scored

The historical regression asks whether extraction still returns the immutable
facts declared by each fixture. It does not require every fixture to represent
success.

Ad hoc Session scoring asks whether the target environment level was reached,
its Timeline/action-event/model-snapshot evidence is complete, and no run
failure or interruption preceded that target. A failure after the target does
not invalidate the completed stage:

```bash
uv run python -m beat_arc_agi_3 eval session \
    --session SESSION_ID \
    --target-level 1
```

Actions and turns to target, checked prediction accuracy, historical duration,
and completed tool-call counts are metrics. They are not pass conditions. The
two known successes both took 25 actions and 11 turns, but differed at 9 action
positions and used substantially different tool mixes. Exact action or tool
trajectory matching would therefore reject valid policies and is not used.

`SessionStageTask` opens and validates each Session, then extracts facts from
the append-only Timeline and event journal. The task records those facts through
Pydantic Evals metrics and attributes. `SessionEvidenceRegressionEvaluator`
compares historical and synthetic fixtures with expected facts;
`StageOutcomeEvaluator` scores a new Session's target outcome. Both are
deterministic. There is no LLM judge and no Logfire or OpenTelemetry
requirement.

## Per-level lifecycle report

Use the process report to compare where an agent spent its steps and how its
synthesis loop changed from level entry to exit:

```bash
uv run python -m beat_arc_agi_3 eval lifecycle --session SESSION_ID
```

The command emits deterministic JSON and performs no model request or ARC
action. Each transition is assigned to the level on which its action began.
For every observed level, the report includes entry and exit transition/turn,
action and click-coordinate distributions, exact/mismatch/unchecked counts,
distinct observable states, model installs and backtests, mismatch-to-next-green
repair spans, structured BFS outcomes, committed queue sizes and cancellations,
death/reset/progress/win facts, failures/interruption, and tool counts grouped
into grounding, synthesis, verification, and search according to fixed tool
contracts. These are process measurements, not success criteria and not an
inference about the model's private intent.

## Iterative agent-development loop

For one agent or harness change: identify one failure from preserved Session
evidence, add the smallest deterministic regression that captures it, implement
one change, run free tests, then deliberately run one fresh paid ARC Session.
Score that Session with `eval session` and inspect its trace. Preserve both
successes and failures. Repeated baselines, statistical experiment reporting,
and richer telemetry remain parallel additions when a concrete comparison or
debugging question requires them.
