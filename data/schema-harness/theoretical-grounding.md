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

The 1,206 classified backtest mismatches are counterexamples found in already recorded evidence. The 3,627 `model_mispredicted` events are counterexamples generated by new interaction. Together they expose the two checker layers described earlier.

The fact that `edit_file`, `write_file`, and `commit_actions` appear in all 50 traces indicates that candidate synthesis, persistent artifacts, and experimental interaction are structural features rather than idiosyncratic strategies.

The fact that BFS appears in 45 of 50 traces—but only 462 times—supports the separation between model acquisition and downstream planning. Most effort is spent making the graph trustworthy enough to search.

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

## Strong theoretical claims versus useful analogies

### Directly grounded claims

- The world model is a synthesized program constrained by execution traces.
- The task is a form of reverse engineering as presented in Lecture 1.
- Recorded transitions define a finite inductive specification.
- Backtesting computes historical consistency.
- New evidence shrinks the conceptual version space.
- Prediction failures act as counterexamples.
- The edit/backtest loop is a form of LLM self-repair.
- BFS is model-based search over the synthesized transition system.
- The overall architecture is a hybrid of LLM-in-control and program-in-control.

### Useful but incomplete analogies

- Schema is CEGIS-like, but lacks a complete verifier.
- Probes resemble membership queries, but queries are stateful and costly.
- The architecture is neurosymbolic, but does not use the specific differentiable methods from Lecture 16.
- Model transitions fit MDP notation, but the agent is not trained by RL.
- File edits resemble evolutionary mutations, but the trace loop is not a full evolutionary algorithm.
- Candidate snapshots resemble a version space, but do not symbolically represent all consistent programs.

### Claims the evidence does not support

- A green backtest proves the game has been reverse engineered.
- BFS proves a real plan exists.
- The final model is equivalent to the game's source implementation.
- The traces implement formal verification.
- The agents optimize information gain explicitly.
- The agents learn a policy through reinforcement learning.
- The candidate model is minimal or unique.

## A theoretically grounded name for the loop

For future design and writing, the loop can be named:

> **Counterexample-Guided Active World-Program Synthesis**

Its stages are:

1. **Represent:** choose or revise the state abstraction.
2. **Synthesize:** write a candidate transition program and goal predicate.
3. **Check:** replay all accumulated trace constraints.
4. **Discriminate:** choose a probe where plausible models may differ.
5. **Act:** execute one action under runtime prediction monitoring.
6. **Refute:** turn any disagreement with reality into a counterexample.
7. **Plan:** when confidence is sufficient, search the candidate model for a goal path.
8. **Guard:** validate every real step and abort stale plans immediately.

This formulation separates model inference, experiment design, planning, and execution safety while showing how counterexamples connect them.

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

That is the theoretical core worth carrying into our ARC-AGI-3 harness. The outer Pydantic AI loop is orchestration. The substantive method is the disciplined cycle of representation, synthesis, checking, experimentation, counterexample acquisition, and model-relative planning.
