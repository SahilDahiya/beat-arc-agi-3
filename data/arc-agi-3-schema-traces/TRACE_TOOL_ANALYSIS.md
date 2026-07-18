# Schema Harness Trace Tool Analysis

This document records a repository-local audit of the tool usage in the downloaded Schema Harness ARC-AGI-3 traces. Its purpose is to make the traces easier to study and to preserve the architectural lessons needed when designing our own agent harness.

The central finding is that Schema Harness behaves like a counterexample-guided program-synthesis system:

> The agent proposes an executable world model, tests it against recorded transitions, searches inside that model, acts in the real environment, and uses every prediction failure as a counterexample from which to revise the model.

The model does not merely inspect a grid and choose an action. It maintains durable knowledge, writes executable hypotheses, validates those hypotheses, and only then uses them to plan.

## Audit scope

The audit covered:

- 50 trajectory directories.
- All 50 trajectory-level `events.jsonl` streams.
- All 50 preserved provider session logs.
- 32,356 harness tool invocations.
- 22,184 actions actually executed in ARC environments.
- 3,627 recorded model-misprediction events.

The event streams contain 32,356 `tool_started` events and 32,355 `tool_finished` events, leaving one started invocation without a corresponding finish event in the collected data.

The provider session logs were analyzed separately from the normalized harness events. This matters because Claude and GPT used different orchestration wrappers while ultimately accessing the same underlying harness capabilities.

Counts in this report describe calls, not unique models or discoveries. For example, thousands of green backtests include repeated validation of evolving versions of the same world model.

## Tool inventory

| Tool | Calls | Claude | GPT | Traces | Reported errors | Principal purpose |
|---|---:|---:|---:|---:|---:|---|
| `edit_file` | 9,536 | 2,623 | 6,913 | 50/50 | 214 | Incrementally update world models and notes |
| `run_python` | 6,787 | 3,210 | 3,577 | 49/50 | 64 | Analyze grids/history, test hypotheses, and run custom searches |
| `run_backtest` | 5,931 | 1,305 | 4,626 | 49/50 | 4 | Replay recorded transitions through the candidate model |
| `commit_actions` | 5,434 | 2,542 | 2,892 | 50/50 | 2 | Submit probes or complete plans to the real environment |
| `read_file` | 2,141 | 246 | 1,895 | 47/50 | 1 | Reload models, notes, framework files, and candidates |
| `write_file` | 600 | 280 | 320 | 50/50 | 9 | Seed or replace models, notes, and search programs |
| `grep` | 589 | 70 | 519 | 37/50 | 3 | Locate model functions, constants, and framework behavior |
| `run_bfs` | 462 | 156 | 306 | 45/50 | 12 | Search the learned world model for a goal-reaching plan |
| `cp` | 397 | 20 | 377 | 10/50 | 4 | Snapshot, promote, and restore model versions |
| `read_history` | 341 | 78 | 263 | 41/50 | 0 | Inspect selected real transitions in structured form |
| `run_shell` | 102 | 93 | 9 | 18/50 | 3 | Inspect workspace and runtime artifacts |
| `find` | 35 | 3 | 32 | 15/50 | 0 | Inventory candidates, snapshots, and framework files |
| `rm` | 1 | 0 | 1 | 1/50 | 0 | Remove one temporary notes file |

There were 316 tool results classified as errors, about 0.98% of all calls. Most were ordinary development failures rather than harness instability: stale exact-edit strings, exploratory Python timeouts, malformed arguments, or search timeouts.

## Detailed tool behavior

### `edit_file`

`edit_file` was the most frequently used tool and the main mechanism through which hypotheses became executable models.

Target distribution:

- Live world model: 6,458 calls.
- Durable notes: 2,591 calls.
- Other Python files: 250 calls.
- Candidate models: 228 calls.
- Search programs: 8 calls.
- Other files: 1 call.

The tool used exact `old_string` to `new_string` replacement. Agents used it to:

- Add newly discovered objects and mechanics.
- Correct transition behavior exposed by counterexamples.
- Change latent-state representations.
- Add terminal-state detection.
- Revise `is_goal` for model-based search.
- Tune movement, timing, collision, resource, and reset rules.
- Keep `notes.md` synchronized with discoveries.
- Make narrow fixes without rewriting a working model wholesale.

The 214 errors were dominated by `old_string not found`, usually because the target file had changed since the agent last read it. This is evidence of normal iterative model development and occasional stale context.

The frequency of this tool shows that successful trajectories did not converge through one large model-generation step. They repeatedly made small, falsifiable revisions.

### `run_python`

`run_python` was the general-purpose scientific workbench. It gave the agent analytical freedom beyond the fixed history and search tools.

Observed uses included:

- Loading grids into NumPy arrays.
- Comparing before and after states.
- Finding changed cells and bounding boxes.
- Segmenting connected components.
- Identifying repeated objects, colors, masks, and spatial relationships.
- Parsing raw `events.jsonl` records.
- Grouping transitions by action or outcome.
- Reconstructing latent state from long histories.
- Testing candidate transition functions outside the live model.
- Simulating possible action sequences.
- Implementing custom BFS or domain-specific search.
- Fitting movement, timing, or resource parameters.
- Comparing candidate-model predictions against actual observations.

The categories overlap because a single Python call often analyzed history, extracted objects, and tested a model simultaneously. Approximate observed category counts were:

- Grid or object analysis: 5,598 calls.
- History or event analysis: 5,161 calls.
- Model simulation or testing: 2,985 calls.
- Custom search: 1,030 calls.
- Explicit parameter fitting: 29 calls.
- Other ad hoc analysis: 350 calls.

Runtime statistics:

- Median: 0.57 seconds.
- 90th percentile: 6.89 seconds.
- Maximum: approximately 300.6 seconds.

The 64 errors were mostly timeouts and mistakes in exploratory scripts.

An important design lesson is that `read_history` alone was not sufficient. Strong agents needed unrestricted computation over the transition corpus for bespoke inference and debugging.

### `run_backtest`

`run_backtest` was the empirical verification boundary between a plausible hypothesis and a historically consistent world model.

It replayed recorded transitions through the installed candidate model and checked:

- Predicted grid against actual grid on applicable transitions.
- Predicted `level_up` flag.
- Predicted `dead` flag.
- Predicted `win` flag.

Reset transitions and transitions without a prior grid could be skipped where comparison was not meaningful.

On mismatch, its diagnostics included:

- The failing transition index.
- The action that triggered the divergence.
- Predicted and actual terminal flags.
- Predicted and actual grids.
- Coordinates and values of differing cells.

Classified outcomes:

- Exact or green: 4,717 calls.
- Mismatch or counterexample: 1,206 calls.
- Tool execution error: 4 calls.
- Unclear result shape: 3 calls.

Frequently used `max_details` values:

- `1`: 2,155 calls.
- `2`: 1,390 calls.
- `0`: 947 calls.
- `3`: 736 calls.
- Default: 527 calls.
- `5`: 119 calls.

Runtime statistics:

- Median: 2.54 seconds.
- 90th percentile: 62 seconds.
- Maximum: approximately 260 seconds.

A green result meant only that the model explained the selected recorded history. It did not establish that the model was correct on unseen states or actions. The environment frequently produced new counterexamples after a green backtest.

When all relevant transitions passed, the output explicitly indicated that the model was safe to use for BFS. This established an intended workflow: validate first, search second.

The four tool errors arose from restricted execution encountering unavailable built-ins such as `globals` or `next`.

### `commit_actions`

`commit_actions` was the only direct bridge from model reasoning to real environment interaction.

Its normal arguments were:

- `actions`: one probe or an ordered plan.
- `reason`: the purpose or justification for the queue.
- `suggestion`: durable guidance for the next reasoning turn.
- `intent`: a rarely used alternative field.

Argument presence:

- `actions`: 5,434 calls.
- `reason`: 5,413 calls.
- `suggestion`: 5,329 calls.
- `intent`: 21 calls.

Queue statistics:

- Minimum length: 1 action.
- Median length: 4 actions.
- 90th percentile: 19 actions.
- Maximum length: 387 actions.
- Multi-action queues: 3,673.
- Queues containing coordinate clicks: 2,463.

The call immediately ended the current agent turn. The agent could not perform further analysis after committing. Consequently, `suggestion` acted as an explicit handoff message to the next turn. It commonly said what result to inspect, what hypothesis was being tested, or what should happen if the plan failed.

The harness checked the active world model after each real action. When predicted and actual observations diverged:

1. The unexpected transition was recorded.
2. A `model_mispredicted` event was emitted.
3. The unexecuted suffix of the queue was dropped.
4. A new reasoning turn began with the counterexample available.

The traces contain 3,627 such misprediction events.

This explains why queued action counts substantially exceed actual environment actions. The agents planned many long sequences, but the harness executed only 22,184 actions because prediction errors frequently interrupted queues.

A recurring risk-management strategy was to place the least certain action at the end of a queue. If it falsified the model, no valuable plan suffix would be lost.

The two argument errors passed scalar action codes instead of action objects.

### `read_file`

`read_file` recovered durable state and inspected relevant code.

Target distribution:

- Live world model: 1,690 calls.
- Notes: 314 calls.
- Framework source: 57 calls.
- Candidate models: 29 calls.
- Other Python files: 28 calls.
- Data or text files: 12 calls.
- History artifacts: 8 calls.
- Snapshots: 3 calls.

Agents used it after turn boundaries, context compaction, candidate promotion, or failed edits. The median response was approximately 4.2 KB; the largest was approximately 50 KB.

The usage pattern demonstrates that filesystem state, especially `notes.md` and `world_model_v5.py`, was treated as authoritative long-term memory. Conversation context was temporary.

The single error attempted to read `world_model_v5.py` before it existed.

### `write_file`

`write_file` was used for initial creation and substantial replacement rather than narrow iteration.

Target distribution:

- Notes: 330 calls.
- Live world model: 228 calls.
- Other Python files: 15 calls.
- Search programs: 14 calls.
- Candidate models: 5 calls.
- Data or text files: 5 calls.

A common opening sequence was:

1. Write a durable notes document.
2. Write an identity or minimal world model.
3. Install it as `world_model_v5.py`.
4. Run an initial backtest.
5. Commit a small real-world probe.

Writing the live model path automatically installed the model. The output reported whether the module exposed:

- A stateless `step` interface.
- A stateful `predict` interface.
- An `is_goal` function suitable for search.

It then recommended running a backtest before trusting the model.

The nine errors mostly came from invalid model code or unavailable restricted-runtime built-ins.

### `grep`

`grep` provided targeted navigation in models and framework files. It was used to:

- Locate `step`, `predict`, and `is_goal`.
- Find a state variable or constant.
- Inspect a specific mechanic without rereading a large model.
- Determine whether notes already documented an observation.
- Locate relevant framework implementation.

Most calls targeted the live world model. The three failures were two unreadable-path attempts and one malformed regular expression.

### `run_bfs`

`run_bfs` searched the learned simulator rather than the real ARC environment.

Goal targets:

- `level_up`: 205 calls.
- `advance`: 124 calls.
- `is_goal`: 74 calls.
- Default target: 49 calls.
- `win`: 10 calls.

Search bounds:

- Minimum maximum depth: 1.
- Median maximum depth: 24.
- 90th percentile maximum depth: 55.
- Largest maximum depth: 149.
- Minimum node budget: 10.
- Median node budget: 100,000.
- 90th percentile node budget: 900,000.
- Largest node budget: 4,000,000.

Action-space statistics:

- Median click-candidate count: 4.
- 90th percentile click-candidate count: 12.
- Maximum click-candidate count: 150.
- Median non-click action-candidate count: 4.
- Maximum non-click action-candidate count: 6.

Successful output could report:

- The goal predicate used.
- Number of expanded nodes.
- Number of distinct states.
- The action and click candidates considered.
- An exact action plan formatted for `commit_actions`.
- The predicted final grid.

At least 281 outputs were clearly classified as plan-found results. Nine explicitly reported exhaustion or no plan, and 160 did not match the conservative result classifier. Twelve calls failed, primarily because search timed out.

Runtime statistics:

- Median: 10.66 seconds.
- 90th percentile: approximately 602 seconds.
- Maximum: approximately 641 seconds.

BFS completeness was conditional on four things:

1. The correctness of the world model.
2. The completeness of its state representation.
3. The supplied action and click candidates.
4. The configured depth and node budgets.

As a result, BFS could find a mathematically valid plan for an incorrect simulator. Backtesting reduced this risk but could not eliminate errors on unseen states.

`run_bfs` was not universal. Some agents constructed plans directly or wrote domain-specific search programs through `run_python`.

### `cp`

`cp` functioned as lightweight model version control. Although only 10 trajectories used it, those trajectories used it heavily.

Typical operations were:

- Copy the live model into a candidate checkpoint.
- Snapshot a working model before a risky rewrite.
- Promote a candidate to `world_model_v5.py`.
- Restore an earlier candidate.
- Preserve level-specific model versions.

Copying a file into the live model path also installed it and produced the same interface report as `write_file`.

The four failures came from copying a path onto itself or malformed copy arguments.

### `read_history`

`read_history` offered structured, selective access to real environment transitions.

Supported selection patterns included:

- Explicit transition indices.
- Start and end ranges.
- Result limits.
- Action-code filters.
- Terminal-flag filters.
- Brief, full, and animation detail levels.

Detail-level usage:

- Brief: 182 calls.
- Full: 109 calls.
- Animation: 48 calls.
- Default: 2 calls.

Its output could summarize:

- Total transition count.
- Level-ups, deaths, wins, and resets.
- Click count.
- Counts by action.
- Maximum observed level.
- Before and after grids.
- Number of changed cells.

Agents used it to find discriminating examples, such as every death transition or every instance of a particular action, before changing the model. It was the fastest path for focused inspection, while `run_python` handled custom aggregation and inference.

No `read_history` errors were observed.

### `run_shell`

`run_shell` was a secondary development and inspection tool rather than a gameplay capability.

Observed uses included:

- Listing workspace files.
- Inspecting line counts and file fragments.
- Comparing candidate models with `diff`.
- Searching event logs.
- Inspecting framework or runtime artifacts.
- Looking at active processes.

Claude used it far more frequently than GPT. The three failures omitted the required command argument.

### `find`

`find` was used to inventory:

- Candidate models.
- Snapshots.
- Workspace artifacts.
- Framework source files.

It had no direct role in environment interaction and produced no errors.

### `rm`

`rm` appeared once, deleting a temporary `notes.md.tmp` file. It had no gameplay or modeling role.

## Provider integration differences

The normalized event streams expose the 13 harness tools above. The preserved provider sessions also expose orchestration mechanisms used to reach those tools.

### Claude sessions

Claude commonly used `ToolSearch` before making direct MCP calls under a `mcp__locus__...` namespace.

Representative preserved-session counts:

- `mcp__locus__run_python`: 3,087.
- `mcp__locus__commit_actions`: 2,509.
- `mcp__locus__edit_file`: 2,505.
- `mcp__locus__run_backtest`: 1,239.
- `mcp__locus__write_file`: 261.
- `mcp__locus__read_file`: 240.
- `mcp__locus__run_bfs`: 135.
- `ToolSearch`: 46.
- `ScheduleWakeup`: 4.

### GPT sessions

GPT commonly used an `exec` orchestration wrapper and invoked normalized `mcp__arc__...` tools inside it. Long-running calls were resumed with `wait`.

Representative wrapper counts:

- `exec`: 19,075.
- `wait`: 5,429.

Approximate nested harness calls included:

- `edit_file`: 6,152.
- `run_backtest`: 4,218.
- `run_python`: 3,299.
- `commit_actions`: 2,617.
- `read_file`: 1,765.
- `grep`: 478.
- `cp`: 376.
- `run_bfs`: 303.

`ToolSearch`, `exec`, `wait`, and `ScheduleWakeup` are provider/runtime mechanisms. They should not be mistaken for ARC reasoning capabilities. The meaningful portable interface is the normalized harness tool set.

## Reconstructed agent workflow

Across providers and games, the common workflow was:

1. Discover the available tools.
2. Create `notes.md` and a minimal executable `world_model_v5.py`.
3. Run a baseline backtest.
4. Commit a small, information-producing probe.
5. Inspect the resulting transition with `read_history` or `run_python`.
6. Form a hypothesis about the observed mechanic.
7. Encode that hypothesis in the world model.
8. Replay historical transitions with `run_backtest`.
9. Treat every mismatch as a concrete counterexample.
10. Repeat model revision and validation until sufficiently consistent.
11. Use `run_bfs`, custom Python search, or direct reasoning to construct a plan.
12. Submit the plan with `commit_actions`.
13. Check the model's prediction after each real action.
14. Abort the remaining plan at the first mismatch.
15. Add the new transition to history, revise the model, and replan.
16. Preserve useful candidates and discoveries in files.

In compact form:

```text
observe history
      |
      v
infer mechanic --> edit executable model
      ^                    |
      |                    v
new counterexample <-- backtest history
      ^                    |
      |                    v
real environment <-- commit plan <-- model search
        prediction gate
```

## Representative trajectory styles

Different agents used the same architecture with very different levels of intensity.

### Efficient Fable trajectories

Some Fable trajectories discovered the important affordances quickly and needed relatively little model surgery.

For example, one FT09 trajectory used approximately:

- 15 `commit_actions` calls.
- 29 `edit_file` calls.
- 17 backtests.
- 8 Python analyses.
- 2 BFS calls.

An SB26 Fable trajectory used:

- 12 `commit_actions` calls.
- 20 edits.
- 10 backtests.
- 11 Python analyses.
- 1 BFS call.

### Long iterative trajectories

A Claude Opus LS20 trajectory used:

- 110 `commit_actions` calls.
- 280 edits.
- 100 backtests.
- 230 Python analyses.
- 56 BFS calls.

This represents a sustained cycle of model refinement and repeated planning.

### Code- and verification-heavy GPT trajectories

A GPT max KA59 trajectory was the most intensive model-development example:

- 326 `commit_actions` calls.
- 1,047 edits.
- 703 backtests.
- 370 Python analyses.
- 493 file reads.
- 200 grep calls.
- 133 copies/checkpoints.
- 53 history reads.
- 40 BFS calls.

A GPT xhigh WA30 trajectory used:

- 313 `commit_actions` calls.
- 610 edits.
- 498 backtests.
- 536 Python analyses.
- 221 file reads.
- 41 model copies.
- 17 BFS calls.

These trajectories treated world-model development like an extended software-engineering process, with validation, inspection, and versioning dominating the work.

## Architectural conclusions for our harness

The traces imply that the world-model and verification substrate should be designed before the outer Pydantic AI loop.

### 1. Transition history must be first-class

The harness should preserve every real transition with:

- Pre-action observation.
- Structured action.
- Post-action observation.
- Level, death, win, and reset flags.
- Model prediction active at execution time.
- Predicted-versus-actual difference.
- Plan and queue provenance.

The agent should be able to query history structurally and analyze the raw corpus programmatically.

### 2. The world model needs a stable executable contract

The traces rely on a replaceable module exposing something equivalent to:

- A stateless transition function or stateful predictor.
- A serializable model state.
- Terminal-condition outputs.
- A goal predicate for search.

Installing a new model should validate its interface and isolate execution failures.

### 3. Exact replay is the main verification primitive

Backtesting should:

- Replay selected or complete history.
- Compare grids exactly.
- Compare all terminal flags.
- Identify the first failing transition.
- Produce compact cell-level diagnostics.
- Allow diagnostic verbosity to be controlled.

Green backtests must be described as historical consistency, not proof of correctness.

### 4. Action queues need a prediction gate

Long plans are useful only when execution is guarded after every action. The harness should:

- Execute one queued action.
- Obtain the real observation.
- Run the model's corresponding prediction.
- Compare actual and predicted outcomes.
- Continue only if the prediction passes.
- Record the counterexample and discard the suffix otherwise.

This mechanism turns risky execution into an additional source of model evidence.

### 5. Turn handoff must be explicit

Because committing actions ends a reasoning turn, the tool should preserve:

- Why the action or plan was selected.
- What uncertainty it tests.
- What the next turn should inspect.
- What should happen after success or failure.

This is more reliable than expecting conversational context to carry the plan across turns.

### 6. Search must remain subordinate to validation

BFS or another planner should consume the same installed model that backtesting validates. Search results should retain:

- Model version or content hash.
- Initial modeled state.
- Goal predicate.
- Candidate action set.
- Depth and node limits.
- Predicted terminal state.

A plan generated from one model version should not silently execute after that model changes.

### 7. Durable files are part of agent memory

The traces repeatedly use notes, candidate models, search scripts, and snapshots. Our harness should expect the agent to maintain artifacts outside its prompt context rather than treating filesystem tools as incidental conveniences.

### 8. General-purpose computation is necessary

Fixed analytical tools help, but they cannot anticipate every game mechanic. The agent needs a controlled Python execution surface for:

- Grid algebra.
- Object extraction.
- Statistical analysis.
- Candidate simulation.
- Bespoke search.
- Counterexample reduction.

### 9. Tool latency and limits affect reasoning strategy

Backtests and BFS calls sometimes ran for minutes. The outer agent loop must support long-running operations, result resumption, timeouts, and compact progress reporting without losing turn state.

## Minimum capability set suggested by the traces

Before implementing the agent's reasoning policy, the harness should eventually provide equivalents of:

1. `read_history`
2. Raw transition-data access
3. `write_file`, `read_file`, and `edit_file`
4. Safe Python execution
5. World-model installation and validation
6. Exact historical backtesting
7. Model-based BFS or a planner interface
8. Prediction-gated `commit_actions`
9. Structured model-misprediction events
10. Durable turn-to-turn handoff metadata

The outer Pydantic AI agent can then orchestrate these primitives. The traces indicate that implementing the conversational loop first would invert the dependency: the most important intelligence amplification comes from executable hypotheses, exact replay, and controlled falsification.

## Final interpretation

Schema Harness is best understood as a laboratory for active world-model synthesis:

- `commit_actions` performs experiments.
- `read_history` and `run_python` inspect evidence.
- `write_file` and `edit_file` encode hypotheses.
- `run_backtest` attempts to falsify them using known evidence.
- `run_bfs` derives plans from surviving hypotheses.
- Prediction-gated execution obtains the next counterexample.
- Notes and model files preserve accumulated knowledge.

The traces therefore provide more than examples of successful ARC gameplay. They expose a reusable architecture for agents that learn interactive systems by alternating between experimentation, executable modeling, verification, and planning.
