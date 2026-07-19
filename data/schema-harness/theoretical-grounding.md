# Theoretical Grounding for Schema-Style ARC-AGI-3 Reverse Engineering

This document maps the observed Schema Harness architecture and trace behavior to the concepts in MIT's 2025 *Introduction to Program Synthesis* course. It is an interpretation of the downloaded course material and Schema traces, not a description supplied by the Schema authors.

Companion material:

- [Schema article synthesis](article.md)
- [Schema trace tool analysis](../arc-agi-3-schema-traces/TRACE_TOOL_ANALYSIS.md)
- [MIT synthesis course index](../synthesis-course/2025/index.md)

## Thesis

The most precise theoretical description of Schema is:

> **Active, trace-based, LLM-guided inductive synthesis of an executable model of a black-box reactive system, coupled to model-based planning and prediction-gated execution.**

Shorter descriptions such as “an LLM agent,” “CEGIS,” “model-based RL,” or “program synthesis” each capture only part of the system.

Schema combines several ideas:

1. **Reverse engineering by program synthesis:** infer a high-level executable description of an inaccessible implementation.
2. **Programming by demonstration from traces:** treat observed transitions as examples constraining the program.
3. **Version-space refinement:** each observation removes world models inconsistent with accumulated evidence.
4. **Counterexample-guided repair:** use exact prediction failures to revise the candidate program.
5. **Active experiment selection:** choose real actions that reveal unknown mechanics or distinguish hypotheses.
6. **Neural-guided symbolic synthesis:** use an LLM to write and repair symbolic code, while code performs exact checking and search.
7. **Model-based planning:** search trajectories inside the synthesized transition model.
8. **Runtime prediction monitoring:** stop executing a plan as soon as reality falsifies the model on which it depends.

The core intellectual move is to treat an ARC-AGI-3 game as an unknown program and gameplay as an experiment for inferring that program.

## Why this is genuinely reverse engineering

[Lecture 1](../synthesis-course/2025/Lecture1.md#program-synthesis-applications) explicitly describes reverse engineering as the synthesis problem obtained by reversing the usual direction:

- Ordinary synthesis begins with a specification and seeks an implementation.
- Reverse engineering begins with an implementation and seeks a specification or higher-level model of its behavior.

The lecture gives two especially close precedents.

First, it discusses synthesizing models of reactive frameworks such as Android and Java Swing by recording interactions and forcing a synthesizer to produce a model consistent with those traces. This is structurally close to Schema:

| Reactive-framework modeling | Schema |
|---|---|
| Framework implementation is unavailable or inconvenient to analyze | ARC game rules are hidden |
| Test application interacts with the framework | Agent acts in the game |
| Interaction traces are recorded | Timeline records state/action/state transitions |
| Synthesizer produces a behavioral model | LLM writes `world_model_v5.py` |
| Model supports downstream symbolic analysis | World model supports backtesting and BFS |

Second, Lecture 1 describes synthesizing biological regulatory models from experiments. Multiple models may explain existing data, so automated testing proposes experiments that distinguish them. That is almost exactly the theoretical role of Schema's probing actions: do not merely collect more transitions; choose transitions whose outcomes discriminate among plausible mechanics.

Lecture 1 also cites **WorldCoder**, whose title describes building world models by writing code and interacting with an environment. Schema belongs in this same conceptual family.

The inferred artifact is not the game's original source code. It is a behaviorally useful executable abstraction. Therefore the right goal is not source recovery but **behavioral model lifting**: move from low-level observations to a compact program that predicts the relevant dynamics.

## Formalizing the reverse-engineering problem

Let the hidden game be a reactive system with latent state (x_t), action (a_t), observation (o_t), and terminal signals (z_t):

\[
x_{t+1} = F^*(x_t, a_t)
\]

\[
o_t = G^*(x_t)
\]

\[
z_t = Z^*(x_t, a_t, x_{t+1})
\]

Here, (z_t) includes signals such as level advancement, death, and win. The true functions (F^*, G^*, Z^*) and the latent state (x_t) are unknown.

The trace archive exposes finite evidence:

\[
D_t = \{(o_i, a_i, o_{i+1}, z_i)\}_{i=0}^{t-1}
\]

For a partially observable or history-dependent game, a single observation may be insufficient. The candidate model may instead infer modeled state from history:

\[
\hat{s}_t = E_\phi(o_0, a_0, \ldots, o_t)
\]

and predict:

\[
(\hat{s}_{t+1}, \hat{z}_t) = T_\theta(\hat{s}_t, a_t)
\]

\[
\hat{o}_{t+1} = R_\phi(\hat{s}_{t+1})
\]

A synthesized world model is therefore not merely a transition function. Conceptually it is a tuple:

\[
W = (E_\phi, T_\theta, R_\phi, Goal_\psi)
\]

where:

- (E_\phi) grounds visible history into modeled state.
- (T_\theta) encodes the hypothesized mechanics.
- (R_\phi) maps modeled state back to the observable grid when needed.
- (Goal_\psi) identifies modeled success states for planning.

This explains the Schema article's distinction between **state grounding** and **mechanism discovery**. A mismatch can mean either:

- The transition law is wrong.
- The chosen state is not Markovian.
- A hidden variable was omitted.
- An object or relation was represented incorrectly.
- The goal predicate is wrong.

Repairing only (T_\theta) cannot solve errors caused by an inadequate (E_\phi).

## The hypothesis space

[Lecture 2](../synthesis-course/2025/Lecture2.md#framing-the-pbdpbe-problem) frames inductive synthesis around a hypothesis space (H) and asks two questions:

1. How can we find a program that matches the observations?
2. How do we know that it is the intended program rather than one of many accidental fits?

For Schema, the conceptual hypothesis space is:

\[
H = \{W \mid W \text{ satisfies the world-model interface and execution restrictions}\}
\]

In the traces, (H) is not represented by an explicit grammar or symbolic formula. It is an enormous implicit subset of Python, restricted by:

- Required function signatures.
- Available state and action representations.
- Sandboxed execution.
- Exact backtest behavior.
- The LLM's learned distribution over plausible code.
- Existing code and notes supplied in context.
- Agent-created conventions for objects and latent state.

This is a weakness and a strength.

- It is expressive enough to represent unfamiliar game mechanics.
- It is difficult to search systematically.
- It permits accidental, overfit, or unnecessarily complicated models.
- It relies heavily on the LLM prior to keep candidate programs plausible.

Lecture 2 emphasizes that the choice of notation is crucial: a useful synthesis language should be concise and expressive enough for the domain, but not much more expressive than necessary. Schema uses unrestricted-looking Python because the ARC-AGI-3 mechanic space is unknown. A future harness could preserve Python as an escape hatch while supplying a smaller typed library of common grid, object, state-machine, and interaction primitives.

## A Bayesian interpretation

Lecture 2 and [Lecture 3](../synthesis-course/2025/Lecture3.md#bottom-up-search-with-probabilities) give a probabilistic interpretation of inductive synthesis. Applied here, the agent approximately seeks:

\[
W^* = \arg\max_{W \in H} P(W \mid D)
\]

Using Bayes' rule:

\[
P(W \mid D) \propto P(D \mid W)P(W)
\]

The exact backtest behaves like a hard likelihood:

\[
P(D \mid W) =
\begin{cases}
1 & \text{if } W \text{ exactly replays every checked transition} \\
0 & \text{otherwise}
\end{cases}
\]

The LLM, prompt, notes, existing model, and code idioms induce an implicit prior (P(W)). This prior favors some explanations over other historically consistent explanations.

The traces do not explicitly optimize a minimum-description-length objective. Nevertheless, incremental edits, preference for understandable mechanics, and reuse of objects often create an informal simplicity bias. Lecture 3 explains why such a bias is valuable: smaller programs are less likely to fit examples through arbitrary special cases.

This interpretation clarifies the role of durable notes:

- A recorded transition is hard evidence affecting the likelihood.
- A note is a hypothesis, abstraction, or search hint affecting the proposal distribution.
- Confusing the two causes the agent to treat an unverified belief as an observation.

The harness should preserve that distinction.

## Version-space interpretation

[Lecture 6](../synthesis-course/2025/Lecture6.md#version-spaces) defines the version space for hypothesis space (H) and dataset (D) as the programs in (H) consistent with (D):

\[
VS_{H,D} = \{W \in H \mid W \text{ satisfies every example in } D\}
\]

For Schema, exact replay defines:

\[
VS(D_t) = \{W \in H \mid Backtest(W,D_t)=green\}
\]

Every new transition intersects the current version space with one more behavioral constraint:

\[
VS(D_{t+1}) = VS(D_t) \cap VS(\{d_{t+1}\})
\]

This gives a precise meaning to a prediction failure. If the live model (W_t) mispredicts transition (d_{t+1}), then:

\[
W_t \notin VS(D_{t+1})
\]

The model has been eliminated, even if only a small patch is needed to produce a nearby candidate.

Schema does **not** explicitly maintain the version space. It normally materializes one candidate program at a time. Candidate files and `cp` snapshots are a crude finite archive, not a Version Space Algebra. This creates several consequences:

- The agent may forget alternative hypotheses that remain consistent.
- A probe is selected from prose-level uncertainty rather than computed disagreement among candidates.
- A green backtest can create unjustified confidence because ambiguity is invisible.
- Revisions may oscillate between explanations without a structured candidate set.

The version-space view suggests that uncertainty should be represented as disagreement among surviving models, not merely as the LLM saying it is uncertain.

## Programming by demonstration and trace completeness

Lecture 2 distinguishes programming by example from programming by demonstration. Input/output examples constrain final behavior; demonstrations can include richer execution traces.

Schema is closer to programming by demonstration because each example is a state-action-state transition embedded in a trajectory. The ordering matters, and stateful models may depend on the preceding history.

[Lecture 3](../synthesis-course/2025/Lecture3.md#formal-requirements) discusses **trace completeness**: when a program contains recursive or context-dependent behavior, examples may need to include the sub-executions required to interpret that behavior safely.

There is a useful analogy to Schema:

- A transition may look identical under two models when viewed in isolation.
- Its meaning can differ when hidden state or prior actions are included.
- A history fragment can therefore be insufficient to identify the true transition rule.
- Additional targeted trajectories are required to expose context dependence.

Schema partially handles this by replaying complete histories and by supporting stateful predictors. It does not guarantee trace completeness. The environment may simply never expose the context needed to distinguish two models.

This is another reason a green backtest cannot imply correctness.

## Observational equivalence

Lecture 3 defines two programs as observationally equivalent on a finite example set when they produce the same outputs on those examples, even if they differ elsewhere.

For world models (W_1) and (W_2):

\[
W_1 \equiv_D W_2
\quad\text{iff}\quad
Replay(W_1,D)=Replay(W_2,D)
\]

All green models are observationally equivalent on the checked history. They may predict very different outcomes for an untried action or unseen state.

This concept explains several trace phenomena:

- A wrong rule can remain green because existing trajectories do not distinguish it.
- Two different state representations can fit the same transitions.
- BFS plans can diverge dramatically across backtest-equivalent models.
- A deliberate probe is valuable when it leaves the current observational-equivalence class.

The course describes AlphaCode clustering candidate programs by observational behavior on synthetic inputs. The analogous future mechanism would be:

1. Preserve several backtest-green world models.
2. Generate modeled states and candidate actions.
3. Cluster models by their predicted next observations.
4. Prefer a safe real probe on which clusters disagree.

This turns “try something informative” into an explicit disagreement-based experiment policy.

## CEGIS: the closest algorithmic skeleton

[Lecture 17](../synthesis-course/2025/Lecture17.md#counterexample-guided-inductive-synthesis) presents Counterexample-Guided Inductive Synthesis as a loop between:

- An inductive synthesizer that proposes a candidate satisfying known examples.
- A checker that searches for a counterexample to universal correctness.
- An enlarged example set that constrains the next candidate.

Classical CEGIS can be written as:

```text
D := initial examples
repeat:
    candidate := synthesize(D)
    counterexample := verify(candidate)
    if no counterexample exists:
        return candidate
    D := D ∪ {counterexample}
```

The Schema trace loop is:

```text
D := recorded game transitions
repeat:
    W := LLM-revise-world-model(D, notes, previous-W)
    old_counterexample := replay-check(W, D)
    if old_counterexample exists:
        repair W
        continue

    actions := probe-or-plan(W)
    execute actions one at a time

    if predicted transition differs from reality:
        abort the unexecuted suffix
        D := D ∪ {new transition}
        continue
```

The structural correspondence is strong:

| CEGIS role | Schema mechanism |
|---|---|
| Candidate program | `world_model_v5.py` |
| Inductive synthesizer | LLM using `write_file` and `edit_file` |
| Known examples | Timeline transitions |
| Finite checker | `run_backtest` |
| Counterexample | Earliest replay mismatch or real prediction failure |
| Example accumulation | Append-only transition history |
| Candidate refinement | LLM repair informed by mismatch diagnostics |

However, calling Schema simply “CEGIS” overstates its guarantees.

### Why Schema is not classical verified CEGIS

In classical CEGIS, the verifier attempts to find an input violating the full specification. If no counterexample exists and the verifier is sound and complete for the domain, the candidate is proven correct.

Schema has no such verifier for the hidden game:

- `run_backtest` checks only finite recorded history.
- The real environment accepts actions but does not expose arbitrary internal states.
- Real actions can be costly or irreversible.
- The agent may not be able to reset to every state.
- The true system can contain hidden state.
- The action set considered by a probe policy can be incomplete.
- Absence of a new counterexample means only that none has yet been observed.

Therefore Schema is best called **CEGIS-like counterexample-guided model synthesis**, or **active CEGIS with an experimental black-box oracle**.

The stopping condition is pragmatic—win the game—not proof that (W = W^*).

### Two checker layers

Schema effectively has two different checkers:

1. **Offline finite replay:** `run_backtest` searches existing evidence for a counterexample to the current implementation.
2. **Online experimental checking:** `commit_actions` sends the model into unseen behavior where reality may provide a new counterexample.

The first checker finds regressions and forgotten constraints. The second expands the specification itself.

This two-layer structure is one of Schema's most important departures from textbook CEGIS.

## Self-repair and rejection sampling

[Lecture 11](../synthesis-course/2025/Lecture11.md#self-repair) describes LLM self-repair as:

1. Sample a program.
2. Check it against a constraint.
3. Return the error to the model.
4. Ask for a repaired program.
5. Repeat.

That is the local mechanism behind much of the trace activity:

```text
edit_file -> run_backtest -> mismatch details -> edit_file
```

The 9,536 `edit_file` calls and 5,931 `run_backtest` calls show that the practical synthesizer was not a one-shot code generator. It was an iterative repair process grounded by executable feedback.

Lecture 11 notes that self-repair works only when the model can connect an error to the violated constraint. Schema improves that connection by returning structured diagnostics:

- Failing transition index.
- Triggering action.
- Predicted and actual grids.
- Differing cell coordinates.
- Predicted and actual terminal flags.

These diagnostics are not incidental usability features. They are the information channel from the checker into the inductive synthesizer.

Repeatedly generating a complete model and rejecting it would resemble rejection sampling. Exact localized edits make the proposal distribution conditional on the previous candidate and its concrete error, which is much more efficient when the candidate is already close.

## Active synthesis and experiment design

The finite trace specification is underdetermined. The agent must decide which environment action should produce the next example.

Let (V_t = VS(D_t)) be the surviving version space. An ideal probe would maximize expected version-space reduction:

\[
a_t^* = \arg\max_a
\mathbb{E}_{o' \sim predictions(V_t,a)}
\left[
\log |V_t| - \log |V_{t+1}|
\right]
\]

When real actions have different risks and costs, the objective should include them:

\[
a_t^* = \arg\max_a
\left(
InformationGain(a)
- \lambda Cost(a)
- \mu Risk(a)
\right)
\]

Schema does not explicitly calculate this quantity. The LLM approximates it through reasoning in `reason`, `suggestion`, notes, and analysis code.

The traces nevertheless show the required behavior:

- Minimal probes are committed to isolate an affordance.
- Agents inspect transitions that distinguish competing explanations.
- Uncertain actions are placed at the end of a queue.
- Plans are abandoned on the first surprise.
- Some probes deliberately seek informative mispredictions.

This is closer to **active learning** and **scientific experiment design** than passive imitation.

It also explains the dual role of `commit_actions`:

- **Exploration:** obtain evidence that reduces model uncertainty.
- **Exploitation:** execute a plan believed to reach a goal.

Successful trajectories continually decide which role is currently more valuable.

## Three different searches

The traces contain at least three conceptually distinct search problems. They should not be conflated.

### 1. Synthesis search over programs

Search space:

\[
W \in H
\]

Goal: find an executable model consistent with evidence and useful for planning.

Mechanisms:

- LLM code generation.
- Incremental edits.
- Backtest-guided repair.
- Candidate checkpoints.

### 2. Experiment search over real actions

Search space:

\[
a \in A(o_t)
\]

Goal: choose a safe action or sequence that reveals mechanics or advances the game.

Mechanisms:

- LLM reasoning.
- History analysis.
- Competing predictions.
- Risk-aware queue ordering.

### 3. Planning search over modeled trajectories

Search space:

\[
(a_t, a_{t+1}, \ldots, a_{t+k})
\]

Goal: reach a state satisfying `is_goal` under the candidate model.

Mechanisms:

- `run_bfs`.
- Custom Python search.
- Direct planning for small state spaces.

`run_bfs` performs the third search, not the first. It does not synthesize the world model. It assumes the world model and searches the state graph induced by it.

This distinction explains why exhaustive BFS can still fail in reality: it may be exhaustive over the wrong graph.

## Model-based control, but not reinforcement learning

[Lecture 13](../synthesis-course/2025/Lecture13.md#a-reinforement-learning-primer) defines an environment through states, actions, transitions, rewards, and trajectories. This supplies useful notation for ARC-AGI-3:

- Modeled grid/latent state corresponds to (s \in \mathcal{S}).
- ARC actions correspond to (a \in \mathcal{A}).
- The world model approximates transition function (T).
- Level-up or win supplies sparse goal/reward information.
- A committed action sequence is a rollout.

But the trace process is not reinforcement learning in the usual algorithmic sense:

- No policy parameters are trained by reward gradients.
- No value function is learned from repeated returns.
- No policy-improvement procedure is visible.
- The main learned artifact is executable transition code.
- Planning is primarily BFS or hand-written search.

The more accurate interpretation is **model learning followed by model-based planning**.

The RL framing still exposes a deep issue: Lecture 13 begins with a state space, whereas Schema must discover one. ARC observations may not themselves be Markov states. If two visually identical grids react differently because of hidden history, a stateless grid-to-grid model is structurally incapable of succeeding. Stateful prediction is therefore not an implementation detail; it is a response to partial observability.

## Agent architecture

[Lecture 15](../synthesis-course/2025/Lecture15.md) distinguishes:

- **Program-in-control agents:** code orchestrates LLM calls.
- **LLM-in-control agents:** the LLM chooses and invokes tools or generated code.

Schema is a nested hybrid.

At the deliberation level, it is LLM-in-control:

- The LLM decides whether to inspect, analyze, edit, test, search, or act.
- The LLM writes new code for unanticipated subproblems.
- The LLM selects the next experiment.

At the protocol level, it is program-in-control:

- The harness defines turn boundaries.
- `commit_actions` ends deliberation.
- The harness executes queues one action at a time.
- Prediction mismatch automatically aborts the remaining queue.
- The Timeline is append-only.
- Tools enforce access and runtime constraints.

Inside planning, it becomes program-in-control again:

- BFS systematically explores the model.
- The LLM supplies the model, goal, and action candidates.
- Search returns an exact plan.

This arrangement allocates responsibilities according to comparative advantage:

- LLM: open-ended hypothesis formation, representation invention, code repair, experiment interpretation.
- Program: exact replay, deterministic comparison, exhaustive bounded search, protocol enforcement, persistence.

That division is more theoretically meaningful than simply saying the agent “uses tools.”

## Neurosymbolic interpretation

[Lecture 16](../synthesis-course/2025/Lecture16.md) describes neurosymbolic programming as combining learned systems with symbolic program structure and constraints.

Schema is neurosymbolic in a broad architectural sense:

- A neural language model proposes symbolic code.
- The final world model is executable and inspectable.
- Symbolic execution supplies exact predictions.
- A deterministic checker evaluates historical consistency.
- Symbolic graph search produces action plans.

It is more precise to call this **neural-guided symbolic program synthesis** than a full instance of the specific neurosymbolic techniques in Lecture 16. The traces do not show:

- Differentiable relaxation of the world model.
- Gradient-based fitting of neural components inside the program.
- Distillation from a trained policy.
- Symbolically constrained neural training.

The LLM supplies a proposal prior and semantic invention. The accepted artifact remains symbolic code.

## Tool-by-tool theoretical mapping

| Schema tool or artifact | Theoretical role | MIT course connection | Important qualification |
|---|---|---|---|
| `world_model_v5.py` | Candidate hypothesis/program | Lectures 1, 2, 17 | Behavioral abstraction, not recovered source |
| `write_file` | Initial candidate generation | Lectures 2, 11, 15 | LLM samples code from an implicit Python hypothesis space |
| `edit_file` | Local synthesis/repair operator | Lectures 11, 14, 17 | Resembles mutation, but traces do not implement a full evolutionary population |
| `run_backtest` | Finite constraint checker | Lectures 11, 17, 18 | Historical consistency, not universal verification |
| Backtest mismatch | Counterexample/error signal | Lectures 11, 17 | May expose implementation regression or inadequate state representation |
| `model_mispredicted` | Newly acquired online counterexample | Lectures 1, 17 | Generated by interaction, not a complete equivalence oracle |
| Timeline/history | PBD dataset/specification | Lectures 1, 2, 3 | Ordered traces matter; examples are not independent |
| `read_history` | Example selection and counterexample retrieval | Lectures 2, 3, 17 | Selects evidence but does not generate it |
| `run_python` | Meta-reasoning, feature discovery, custom synthesis/search | Lectures 1, 2, 15 | Unrestricted analytical flexibility beyond fixed tools |
| `commit_actions` used for probes | Membership-query-like experiment | Lecture 1 active disambiguation | Query access is stateful, costly, and constrained by reachability |
| `commit_actions` used for plans | Model-based control | Lecture 13 | Queue is guarded by prediction checks |
| `run_bfs` | Search in the synthesized transition system | Lectures 3, 13, 15 | Plans over the model, not over guaranteed reality |
| `is_goal` | Synthesized/encoded postcondition | Lectures 17, 18 | Goal inference can itself be wrong |
| `cp` and candidates | Explicit candidate archive | Lectures 6, 14 | Not a symbolic version space or true evolutionary population |
| `notes.md` | Durable synthesis context and informal prior | Lectures 11, 15 | Notes are hypotheses, not ground truth |
| `reason` | Experiment/plan rationale | Lecture 15 | Useful provenance, not formal proof |
| `suggestion` | Cross-turn continuation state | Lecture 15 | Compensates for `commit_actions` ending the turn |
| Prediction-gated queue | Runtime monitor and safe falsification loop | Lectures 17, 18 | Detects divergence only after executing an action |
| Tool schemas and model interface | Syntactic constraints over generated behavior | Lectures 1, 2, 4 | Interface validity does not imply semantic validity |

## How the observed tool frequencies support this interpretation

The trace counts are consistent with synthesis-and-verification being the main workload:

- `edit_file`: 9,536 calls.
- `run_python`: 6,787 calls.
- `run_backtest`: 5,931 calls.
- `commit_actions`: 5,434 calls.
- `run_bfs`: 462 calls.

If Schema were primarily a direct policy agent, environment action selection would dominate. Instead, code editing, analysis, and checking dominate. Planning search is important but comparatively rare.

Direct parsing of the first summary line from completed `run_backtest` outputs found 3,837 green results and 2,086 results with one or more mismatches, plus four errors and three empty or unparsed results. One additional `run_backtest` started without a matching finish event. The older coarse classifier used in the first trace-analysis pass substantially undercounted mismatching backtests. The 3,627 `model_mispredicted` events are separate counterexamples generated by new interaction. Together the two populations expose the two checker layers described earlier.

The fact that `edit_file`, `write_file`, and `commit_actions` appear in all 50 traces indicates that candidate synthesis, persistent artifacts, and experimental interaction are structural features rather than idiosyncratic strategies.

The fact that BFS appears in 45 of 50 traces—but only 462 times—supports the separation between model acquisition and downstream planning. Most effort is spent making the graph trustworthy enough to search.

## Empirical anatomy of a level

The preceding sections describe the whole run. A second analysis divided every trace at level boundaries and examined how a level begins, how evidence accumulates, and what happens immediately before advancement.

The archive contains 366 level segments across 50 trajectories. Of these, 365 end in an observed level-up or win and one is incomplete. A level-up action is attributed to the level in which the action began, even though the `action_taken.level` field contains the resulting level. This distinction is necessary to avoid assigning the successful action to the level it just entered.

The stage labels below are interpretations of observable operations:

- **Ground:** inspect the new state, history, notes, or inherited model before taking a real action.
- **Probe:** take an action partly to learn whether a proposed mechanic generalizes.
- **Analyze:** use `run_python`, history inspection, or artifact inspection to explain evidence.
- **Update:** write, edit, or replace the executable world model.
- **Check:** replay accumulated transitions with `run_backtest`.
- **Search:** use `run_bfs` or custom code to search modeled trajectories.
- **Execute:** submit and carry out a committed action queue.
- **Refute:** observe a `model_mispredicted` event and invalidate the remaining queue.
- **Clear:** execute the action that advances the level or wins.

The events establish tool order and action order directly. They do not expose an agent's complete internal intent. Terms such as "probe" and "hypothesis" are therefore justified by explicit commit reasons and surrounding operations, but remain interpretations rather than harness-provided labels.

### The recurring level loop

The most common level lifecycle is:

```text
enter level
    -> ground the new state against the inherited model
    -> submit a probe or provisional plan
    -> execute one real action
    -> if reality disagrees, abort the unexecuted suffix
    -> analyze the counterexample
    -> update the world model
    -> backtest accumulated history
    -> optionally search the model
    -> commit a guarded action batch
    -> clear the level
```

The middle is cyclic. A single level can pass through probe, refutation, update, and checking many times before the final execution batch.

Across the 365 completed level segments:

| Observable behavior | Completed levels | Share |
|---|---:|---:|
| At least one tool before the first real action, including commit | 365 | 100.0% |
| At least one non-commit grounding tool before the first real action | 357 | 97.8% |
| At least one multi-action plan | 358 | 98.1% |
| `run_backtest` used | 352 | 96.4% |
| Live world model written, edited, or replaced | 346 | 94.8% |
| `run_python` analysis used | 338 | 92.6% |
| Durable notes updated | 334 | 91.5% |
| Online model mismatch observed | 323 | 88.5% |
| `run_bfs` used | 157 | 43.0% |
| Level cleared in its first turn | 24 | 6.6% |

Every completed level invokes `commit_actions` before the environment executes its first action, as required by the protocol. Nearly every level also performs substantive non-commit grounding first. No richer tool sequence is literally universal. The stronger recurring structure is near-universal rather than universal:

- 346 levels, or 94.8%, contain a model update followed later by a backtest.
- 352 levels, or 96.4%, contain a backtest followed later by commit and real action.
- The median level contains seven adjacent transitions between model update and verification in its compressed stage sequence; the 90th percentile contains 24.

These measurements support a repeated synthesis-and-repair loop. They do not support a rigid workflow in which every level must invoke every tool exactly once or in a fixed order.

### Level entry is a generalization test

Level zero differs from later levels because the agent initially has little or no executable model. Its first plan is normally one high-information action. In 46 of the 50 level-zero segments, the first commit reason explicitly describes a probe, exploration, or a probe that also makes progress.

Later levels inherit a candidate program. Entry therefore becomes a test of whether previously learned semantics transfer to the new configuration.

| Level | Completed segments | Median tools before first action | First-turn mismatch | Any mismatch | Search used | Median turns |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 50 | 3.5 | 20.0% | 94.0% | 68.0% | 8.0 |
| 1 | 50 | 7.0 | 70.0% | 86.0% | 52.0% | 5.5 |
| 2 | 50 | 7.0 | 74.0% | 92.0% | 40.0% | 7.0 |
| 3 | 50 | 6.5 | 64.0% | 82.0% | 38.0% | 7.0 |
| 4 | 50 | 5.0 | 78.0% | 90.0% | 38.0% | 9.0 |
| 5 | 50 | 5.0 | 78.0% | 92.0% | 32.0% | 9.5 |
| 6 | 31 | 5.0 | 64.5% | 80.6% | 29.0% | 8.0 |
| 7 | 22 | 6.5 | 77.3% | 81.8% | 31.8% | 9.5 |
| 8 | 10 | 4.5 | 60.0% | 100.0% | 60.0% | 18.5 |
| 9 | 2 | 7.0 | 0.0% | 100.0% | 50.0% | 14.5 |

The smaller sample sizes for levels six through nine reflect games with different level counts, not attrition at a common ordinal level.

For levels one through eight, 60–78% of first turns produce a prediction mismatch. The first committed plan may contain several actions, but the median number actually executed in the first turn is one. This reveals an important harness behavior: a later-level plan is often also an experiment. The first novel transition tests the inherited model, and prediction gating prevents the agent from spending the rest of the queue after falsification.

### Synthesis work is front-loaded

Using real environment actions rather than wall-clock time as progress through a level, the distribution of tool calls is:

| Portion of level actions | Share of tool calls |
|---|---:|
| First third | 54% |
| Middle third | 27% |
| Final third | 19% |

Model updates account for 23.3% of tool calls in the first third and 16.9% in the final third. Verification and execution become proportionally more common toward the end. This is consistent with early representation and mechanism discovery followed by increasing exploitation of a stabilized model.

It is not evidence that discovery ends cleanly after the first third. Mismatches and repairs continue late in difficult levels, and the phase boundary is gradual rather than discrete.

### The clearing turn is a model-relative plan

Across completed levels:

- The median final committed queue contains nine actions.
- The median clearing action occurs at position eight in that queue.
- In 347 levels, or 95.1%, advancement is the final planned action.
- The last completed backtest before advancement is green in 301 levels, or 82.5%.
- At least one green backtest appears before advancement in 323 levels, or 88.5%.
- After the final online mismatch, 266 of 323 affected levels, or 82.4%, produce another green backtest before clearing.

This shows that the typical clearing action is the end of a deliberate modeled trajectory rather than an isolated lucky action. It also prevents an overly neat interpretation: 13.7% of levels clear even though the last substantive backtest still reports a mismatch, and 3.6% have no prior substantive backtest. Historical perfection is common but not a necessary stopping condition. The operational objective is a model sufficiently accurate along a useful reachable path, not complete identification of the hidden program.

In 52.9% of completed levels, the last non-commit tool operation in the clearing turn updates durable notes. The remainder end with verification, analysis, search, no preparatory tool, or a rare inspection operation. Notes are therefore part of the practical workflow, but they remain informal synthesis context rather than evidence certified by the checker.

## Grounding the level loop in the MIT course

The level analysis sharpens which course concepts genuinely explain the traces and which provide only analogies.

### Programming by demonstration explains the Timeline

[Lecture 2](../synthesis-course/2025/Lecture2.md#framing-the-pbdpbe-problem) distinguishes input/output examples from demonstrations that include a computation trace. Schema is closer to programming by demonstration because the ordered sequence

```text
state -> action -> state -> action -> state
```

constrains a reactive transition program more strongly than the final level outcome alone.

This makes the Timeline an expanding inductive specification, not merely conversation memory. It also exposes the central under-specification problem from Lecture 2: a candidate can match every observed transition without being the intended transition law.

### Observational equivalence explains new-level failure

[Lecture 3](../synthesis-course/2025/Lecture3.md#simple-bottom-up-search) defines observational equivalence relative to a finite set of inputs. Two world programs can make identical predictions on all recorded history while disagreeing on a new level state.

If (D) is recorded history, then a green result establishes only:

\[
W_1 \equiv_D W_2
\]

It does not establish full behavioral equivalence. The 60–78% first-turn mismatch rate on levels one through eight is an empirical signature of this gap: the inherited program is consistent with much of the previous evidence but often wrong immediately outside that evidence.

A new-level mismatch should therefore not be interpreted only as defective code. It can be the observation that separates hypotheses that were indistinguishable on prior traces. It may reveal a wrong rule, omitted level condition, new object class, hidden variable, inadequate state representation, or wrong goal predicate.

### Version spaces clarify uncertainty but are not implemented

[Lecture 6](../synthesis-course/2025/Lecture6.md#version-spaces) defines the version space as all programs in a hypothesis space that satisfy a dataset. Every new transition conceptually intersects that set with another constraint.

Schema normally materializes one live world model, not a compact symbolic set of all surviving models. Candidate files form a small archive in some traces, but they are not a Version Space Algebra. Consequently:

- A green model hides how many other explanations remain possible.
- Probe selection relies on LLM reasoning rather than computed candidate disagreement.
- The live model is a point estimate, not an explicit uncertainty representation.

The version-space concept explains why probing is needed. It should not be used to claim that the harness implements version-space search.

### Self-repair is the closest local mechanism

[Lecture 11](../synthesis-course/2025/Lecture11.md#self-repair) describes iterative LLM repair driven by checker errors. This directly explains the observed edit/backtest cycles. Structured mismatch diagnostics are the communication channel that lets the LLM associate a failed candidate with a specific violated transition constraint.

This is a stronger and more literal relationship than evolutionary search. Most traces maintain one edited lineage, do not preserve a population, and do not perform crossover.

### CEGIS explains the skeleton, not the guarantee

[Lecture 17](../synthesis-course/2025/Lecture17.md#counterexample-guided-inductive-synthesis) explains why counterexamples make generate-and-check synthesis more efficient: each counterexample constrains future candidates rather than merely rejecting one proposal.

Schema has the same skeleton, but two finite and incomplete checkers:

1. Historical replay finds counterexamples already present in recorded evidence.
2. Guarded real interaction generates new counterexamples on reachable actions.

Neither checker searches every possible game state and action. The loop is therefore **CEGIS-like active model synthesis**, not formally verified CEGIS. Prediction gating adds a runtime-monitoring layer that is operationally important but is not itself the classical CEGIS algorithm.

### Planning is separate from synthesis

[Lecture 13](../synthesis-course/2025/Lecture13.md) supplies useful state, action, transition, and trajectory notation. It helps describe `run_bfs`, but it does not make Schema a reinforcement-learning system. The traces show no reward-gradient training, learned value function, or policy-improvement procedure.

The useful distinction is:

1. Search over candidate world programs.
2. Search over informative real experiments.
3. Search over trajectories inside one selected world program.

`run_bfs` performs the third search. Its result is conditional on the correctness of the state representation, transition model, goal predicate, and candidate actions.

### The architecture is genuinely hybrid

[Lecture 15](../synthesis-course/2025/Lecture15.md) distinguishes program-in-control and LLM-in-control agents. Schema combines them at different layers.

The LLM controls open-ended semantic work:

- Representation invention.
- Hypothesis formation.
- World-model code.
- Counterexample interpretation.
- Experiment selection.
- Choice between direct planning, analysis, and search.

The harness controls exact protocol work:

- Immutable evidence recording.
- Replay and comparison.
- Tool and model interfaces.
- Turn boundaries.
- Action-by-action prediction checking.
- Invalidation of stale queue suffixes.
- Artifact persistence.

The course therefore grounds a useful design rule: **the harness should enforce epistemic discipline while leaving semantic invention to the model**. The traces support recurring stages, not a hard-coded rule that every level must call the same tools in the same order.

## Cross-level model evolution

The level snapshots show whether the inherited world program is replaced, generalized, or extended. Forty-nine traces contain a live world model and cleared-level snapshots. Similarity below is line-based sequence similarity; old-function survival compares the names of Python `def` statements between consecutive snapshots. These are structural proxies, not semantic-equivalence measurements.

| Cleared level | Snapshot count | Median lines | Median similarity to prior snapshot | Median old-function survival |
|---:|---:|---:|---:|---:|
| 0 | 49 | 151 | — | — |
| 1 | 49 | 250 | 0.415 | 83.3% |
| 2 | 49 | 320 | 0.752 | 100.0% |
| 3 | 49 | 401 | 0.815 | 100.0% |
| 4 | 49 | 466 | 0.823 | 100.0% |
| 5 | 49 | 569 | 0.867 | 100.0% |
| 6 | 31 | 633 | 0.916 | 100.0% |
| 7 | 22 | 724 | 0.930 | 100.0% |
| 8 | 10 | 1,094.5 | 0.934 | 100.0% |
| 9 | 2 | 2,371 | 0.990 | 100.0% |

Level one often causes substantial restructuring. From level two onward, the median transition preserves every previously defined function name and adds a small number of functions. The model becomes increasingly similar to its predecessor while continuing to grow.

The most defensible interpretation is **incremental conservative extension under regression testing**:

- Prior mechanics and helper functions are retained.
- New behavior is added through generalization, level-conditioned branches, or special cases.
- Full-history replay discourages regressions on prior evidence.
- The candidate itself can be rewritten non-monotonically even though the evidence set grows monotonically.

There is a partial resemblance to STUN from Lecture 3 because a program that covers one subset of cases is extended or guarded to cover another. The traces do not implement STUN's formal subset search or unification procedure, so the term should remain an analogy.

### Exploration without explicit compression

[Lecture 9](../synthesis-course/2025/Lecture9.md#dreamcoder) describes DreamCoder's exploration-compression cycle: solve a corpus of tasks, discover reusable abstractions, add them to the language, and make future synthesis easier.

Schema visibly performs exploration but does not visibly perform a corpus-level compression phase. The growth from a median 151 lines after level zero to 569 after level five and more than 1,000 after level eight may reflect genuinely accumulating mechanics, over-specialization, or both. Line count alone cannot distinguish them.

The 49 persisted final world models form a corpus from which reusable components could later be studied. The current traces do not support claiming that the harness learns a shared DSL, automatically discovers cross-game components, or optimizes a minimum-description-length objective.

## Strength of the course relationships

The level analysis supports three different confidence classes.

### Strong, direct grounding

- Reverse engineering a black-box reactive implementation from interaction traces: Lecture 1.
- Programming by demonstration and under-specification: Lecture 2.
- Observational equivalence and trace completeness: Lecture 3.
- Iterative LLM self-repair from executable errors: Lecture 11.
- Coupling candidate generation with counterexample-producing checks: Lecture 17.
- Nested program-in-control and LLM-in-control architecture: Lecture 15.

### Useful but incomplete lenses

- Version spaces explain conceptual uncertainty, but Schema stores one main candidate.
- CEGIS explains the loop skeleton, but no complete verifier exists.
- STUN helps describe guarded extension across cases, but no formal unifier is used.
- Bayesian inference helps distinguish the LLM prior from trace likelihood, but no posterior is explicitly represented.
- MDP notation describes planning, but no RL policy is trained.
- Neurosymbolic programming describes the division between neural proposal and symbolic execution, but the specific differentiable techniques in Lecture 16 are absent.

### Relationships the evidence does not support

- Green backtests constitute formal verification.
- A final world model is equivalent to the hidden source implementation.
- Candidate files constitute a Version Space Algebra.
- The agent explicitly maximizes information gain.
- BFS synthesizes the transition model.
- The traces implement reinforcement learning, MCTS, evolutionary populations, or DreamCoder-style library learning.
- Tool schemas or Pydantic output types perform type-directed synthesis of `world_model_v5.py`.

## Refined name for the method

The empirical level lifecycle and the course grounding support the name:

> **Active, counterexample-guided synthesis of a planning model under finite behavioral evidence.**

"CEGIS-like world-model synthesis" remains a useful shorthand, but the longer name preserves the three critical limits:

1. Evidence is selected through costly, path-dependent interaction.
2. Checking is finite and model-relative rather than universal proof.
3. The objective is a successful guarded trajectory, not complete recovery of the hidden program.

## Verification: what is and is not established

[Lecture 17](../synthesis-course/2025/Lecture17.md#interplay-of-verification-and-synthesis) emphasizes that specification, verification, and search are tightly intertwined. Schema demonstrates that principle, but its “verification” is empirical replay.

For a checked dataset (D), a green backtest establishes:

\[
\forall d \in D, \quad W(d) = observed(d)
\]

It does not establish:

\[
\forall x \in \mathcal{X}, \forall a \in \mathcal{A},
\quad W(x,a)=F^*(x,a)
\]

The distinction can be expressed as three levels of confidence:

1. **Syntactic validity:** the model loads and implements the required interface.
2. **Historical consistency:** the model exactly replays selected recorded traces.
3. **Behavioral equivalence:** the model matches the hidden game on every relevant state and action.

Schema directly checks levels 1 and 2. It cannot establish level 3.

[Lecture 18](../synthesis-course/2025/Lecture18.md) distinguishes partial from total correctness. A related distinction applies to plans:

- A BFS result can establish that, **if the modeled transitions are correct and execution follows the modeled path**, the modeled goal will be reached.
- It does not establish that the real game will follow those transitions.
- It also does not necessarily establish that execution is safe outside the modeled assumptions.

Prediction-gated execution turns this limitation into a controlled protocol. Rather than trusting the entire proof in advance, Schema checks its assumptions after every real transition and invalidates the remaining plan when an assumption fails.

This resembles runtime verification more than static proof.

## Invariants and latent state

[Lecture 18](../synthesis-course/2025/Lecture18.md) and [Lecture 19](../synthesis-course/2025/Lecture19.md#synthesis-of-invariants) explain that successful verification often depends on discovering invariants—predicates that remain true across transitions—and ranking functions for termination.

Schema does not explicitly synthesize Hoare-style invariants, but its world models often encode analogous structure:

- Object identities persist across movement.
- Resource counts change according to conservation-like rules.
- A carried-object flag constrains later transitions.
- A phase or toggle mode persists until a specific event.
- A level identifier selects a family of mechanics.
- Goal predicates summarize terminal conditions.

These latent variables make the transition system easier to describe and search. In theoretical terms, state grounding should seek a representation in which important invariants are simple and the next-state function is Markovian.

This suggests evaluating a state representation not only by replay accuracy but also by:

- Simplicity of transition laws.
- Stability of object identities.
- Compactness of required history.
- Ease of expressing invariants.
- Search-state deduplication quality.
- Transfer across levels.

## Component discovery and transfer

[Lecture 9](../synthesis-course/2025/Lecture9.md) presents component discovery as learning reusable abstractions from a corpus of synthesized programs. DreamCoder alternates between solving tasks and compressing common subexpressions into new DSL components.

Schema's individual traces mostly create game-specific code. They do not visibly perform corpus-level component discovery. However, the 50 completed world models form exactly the kind of corpus from which reusable components could be mined:

- Grid differencing.
- Object and connected-component extraction.
- Direction and displacement logic.
- Collision rules.
- Carry/drop state machines.
- Toggle and portal mechanics.
- Level transitions and reset behavior.
- Goal predicates.

Component discovery would be theoretically justified only when a component reduces future search without making the hypothesis language so broad that branching explodes. Lecture 9 emphasizes this tradeoff.

Therefore the right goal is not a giant utility library. It is a compact vocabulary of abstractions repeatedly useful across games, with escape hatches for novel mechanics.

## Evolutionary-search analogy and its limit

[Lecture 14](../synthesis-course/2025/Lecture14.md) describes evolutionary program synthesis in terms of populations, mutation, selection, crossover, and fitness.

Schema has a loose analogy:

- Candidate world model: genome.
- `edit_file`: mutation.
- Backtest score: fitness or hard selection criterion.
- `cp` candidates: small archive.
- LLM: semantically informed mutation operator.

But the traces generally do not implement an evolutionary algorithm:

- They usually maintain one live lineage, not a population.
- There is little or no crossover.
- Selection is dominated by exact consistency, not comparative scalar fitness.
- Revisions are directed by counterexamples rather than random variation.

The better primary model is self-repair plus CEGIS. Evolutionary search becomes relevant only if a future harness maintains multiple competing candidates and uses the LLM to mutate them.

## Where Schema departs from textbook synthesis

Schema adds several complications that classic examples often abstract away.

### The state representation is itself synthesized

Traditional synthesis usually fixes the input and output representation. Schema may have to invent objects, latent variables, temporal context, and goal state.

### The specification grows through interaction

The dataset is not given once at the beginning. The agent chooses actions that determine which examples become available.

### Examples are stateful and path-dependent

The environment cannot necessarily answer an arbitrary query ((s,a)). The agent must reach (s) through a legal trajectory.

### Counterexamples have real cost

A failed query can consume actions, cause death, reset progress, or move the system into a new state.

### The objective is task success, not full identification

The agent only needs a model accurate enough in the relevant region of state space to produce a winning plan.

### The target can be nonstationary across levels

A rule learned on one level may change or gain hidden conditions later. The model may need guarded mechanics or level-dependent structure.

### The verifier and planner depend on the same abstraction

If state decoding is wrong, both backtesting and BFS can agree with one another while being jointly misleading.

These differences make Schema closer to active scientific modeling of a reactive system than to ordinary synthesis from a fixed set of unit tests.

## Theoretical implications for a future harness

These are design conclusions implied by the mapping, not implementation undertaken in this study.

### Preserve the distinction between evidence and belief

The Timeline should contain immutable observations. Notes and model comments should contain interpretations. A hypothesis must not silently become evidence.

### Make candidate identity explicit

Every model revision should have a parent, content hash, claimed change, and backtest result. Plans should record the model revision under which they were generated.

### Represent ambiguity when possible

One green model is not the version space. Preserving several diverse, historically consistent models would expose under-specification and enable disagreement-based probing.

### Treat counterexamples as first-class objects

A counterexample should retain:

- Trace location.
- Pre-state/history.
- Action.
- Predicted and actual outputs.
- Terminal-flag differences.
- Model revision.
- Aborted plan suffix.
- Minimal relevant changed region when available.

### Separate the three searches

The system should distinguish metrics and budgets for:

- Program/model synthesis.
- Real-world experiment selection.
- Planning inside a candidate model.

### Make confidence model-relative and evidence-relative

“Certified” should mean exact on a named dataset under a named replay procedure. It should never mean true in the hidden environment.

### Prefer probes that split hypotheses

When multiple candidates exist, the harness can estimate which reachable action produces the greatest predictive disagreement, then discount it by real-action cost and risk.

### Encourage concise, structured models

A smaller typed vocabulary and reusable grid/state-machine components can supply an explicit prior toward interpretable, transferable models while retaining Python for genuinely novel mechanics.

### Keep planning subordinate to model validation

A planner should consume a frozen model revision, initial state, candidate action set, goal predicate, and search bounds. Its result is conditional evidence, not an unconditional command.

### Preserve runtime falsifiability

Prediction gating is not merely a safety feature. It is the mechanism that keeps planning scientifically accountable to reality.

## Final synthesis

The MIT course gives Schema a coherent theoretical foundation, but no single lecture explains the entire system.

- Lecture 1 explains reverse engineering from interaction traces and active experiment selection.
- Lecture 2 explains inductive synthesis, under-specification, hypothesis-space design, and probabilistic ranking.
- Lecture 3 explains observational equivalence, trace completeness, simplicity priors, and program-space search.
- Lecture 6 explains version spaces and how each example narrows the set of consistent programs.
- Lecture 9 explains how reusable abstractions could eventually be learned across world models.
- Lecture 11 explains hard checking and iterative LLM self-repair.
- Lecture 13 supplies state-transition and model-based-control notation while clarifying why Schema is not ordinary RL.
- Lecture 14 supplies a limited analogy to LLM-guided mutation and candidate selection.
- Lecture 15 explains the nested program-in-control and LLM-in-control agent architecture.
- Lecture 16 explains the broader neural-symbolic division of labor.
- Lecture 17 provides the central CEGIS skeleton and the warning that finite examples do not amount to proof.
- Lectures 18 and 19 clarify correctness, invariants, and the difference between empirical replay and formal verification.

The deepest grounding is therefore:

> Schema turns black-box interaction into an expanding inductive specification, uses an LLM to synthesize an executable symbolic hypothesis, uses replay and reality to falsify that hypothesis, and searches the surviving hypothesis for a plan.

The level analysis makes that cycle empirical rather than merely conceptual: synthesis work is front-loaded, inherited models are frequently falsified by the first novel action, edit/backtest repair repeats within a level, and advancement usually ends a deliberate guarded queue. The resulting method is best described as **active, counterexample-guided synthesis of a planning model under finite behavioral evidence**.

That is the theoretical core worth carrying into our ARC-AGI-3 harness. The outer Pydantic AI loop is orchestration. The substantive method is the disciplined cycle of representation, synthesis, checking, experimentation, counterexample acquisition, and model-relative planning.
