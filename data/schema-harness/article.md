---
title: "Schema: Frontier Models with an Executable World-Model Harness on ARC-AGI-3"
source: https://schema-harness.github.io/
published: 2026-07-15
source_organization: Impossible Research
document_type: high-fidelity study synthesis
companion_traces: ../arc-agi-3-schema-traces/README.md
---

# Schema: an executable world-model harness for ARC-AGI-3

This document is a close, structured synthesis of the interactive Schema article. It preserves the article's claims, numbers, architecture, diagrams, and case-study conclusions in text form while omitting the embedded image and replay payloads. The final section separates our reverse-engineering interpretation from the authors' claims.

Authors: Guanning Zeng, Jiani Wang, Wenjie Ma, Shaofeng Yin, Chenyang Wang, Shichen Liu, Angjoo Kanazawa, Wode Ni, Xiuyu Li, Andrea Zanette, and Haiwen Feng. Affiliations include Impossible Research, the University of California, Berkeley, and Carnegie Mellon University.

## Central claim

Schema is a harness that makes a frontier model approach an unknown game like a physicist. The model must turn perception into an explicit state, express the game's hidden mechanism as executable code, test that code against accumulated evidence, and plan inside the resulting simulator.

The name refers to a rule of construction connecting an abstract concept to concrete perception. In this system, the bridge is literal: raw grids become a coded state representation, and hypotheses about causality become a runnable transition function.

On the 25-game ARC-AGI-3 Public set, the article reports:

- 98.98% RHAE with a retained pairing of Claude Opus 4.8 and Fable 5.
- 95.35% RHAE with a retained pairing of GPT-5.6 Sol xhigh and Sol max.
- 42.83% for a controlled Claude Code scratch-snapshot baseline using the same Opus/Fable pairing.
- 13.33% as the nearest official Public reference for the best individual Sol max variant.

The Schema results are self-reported from the released run artifacts. They were not independently verified by ARC Prize when the article was published, and they do not establish performance on the Semi-private set.

## ARC-AGI-3: games without rule sheets

At each step, ARC-AGI-3 provides a 64×64 grid whose cells use 16 color indices, plus the actions currently legal in the environment. It does not provide an object list, a goal statement, a reward-shaped explanation, or a description of the transition rules.

The agent therefore has to infer all of the following while acting:

- which pixel patterns should be treated as persistent objects;
- which object properties belong in the state;
- how an action changes that state;
- which changes are progress, failure, death, level completion, or game completion;
- which experiment will distinguish competing explanations;
- how to solve efficiently once the mechanism is understood.

This makes interaction inseparable from theory formation. Early actions must serve two purposes at once: move toward a possible goal and reveal causal structure.

The official metric makes inefficient discovery expensive. Relative Human Action Efficiency (RHAE) compares the agent's action count on each completed level with an upper-median first-exposure human baseline. The level score is proportional to:

```text
(human_actions / agent_actions)^2
```

It is capped at 1.15. Later levels receive increasing weights, and a similarly weighted completion cap prevents a game from receiving full credit unless all levels are completed. Every real environment action counts, including probes and failed experiments. Extra actions are penalized quadratically.

The metric therefore rewards three things together:

1. completing levels;
2. discovering mechanics economically;
3. reusing knowledge rather than rediscovering it on every level.

## Two coupled synthesis problems

The article divides the central problem into two layers.

### State grounding

State grounding transforms the raw observation into objects, variables, and relations that can be tracked. The environment never says that a particular shape is a player, another region is a wall, a bar is an action budget, or a pattern is a target. Those categories are invented by the agent because they support a compact explanation of the observed transitions.

The article relates this layer to VIGA, an earlier analysis-by-synthesis system that recovered scene programs from continuous visual input through a graphics engine.

### Mechanism discovery

Mechanism discovery infers how the grounded state changes when an action is applied. Its output is not just a verbal belief. The rule is encoded as an executable program, centered on a function conceptually equivalent to:

```python
next_state = step(state, action)
```

The article relates this layer to WorldCoder, which learns transition programs from trajectories when the state is already structured.

### Why the layers must be revised jointly

A plausible object representation can make every candidate transition rule inconsistent. Conversely, a complicated transition rule may only be compensating for a poor representation. Schema puts both the state interpretation and transition logic in the same editable world-model program.

When a prediction fails, the model may need to revise:

- a parameter inside a known rule;
- the rule's structure;
- an object's properties;
- object identity or persistence;
- hidden state not directly rendered in the current grid;
- the inferred goal predicate itself.

The article emphasizes that repeatedly patching a law is not always enough. Sometimes the counterexample shows that the chosen state variables are wrong. ARC-AGI-3 demands this deeper revision because neither objects nor goals are supplied. Schema represents the inferred goal through an executable predicate such as `is_goal(state)`.

## The Schema control loop

The article's main architecture diagram shows an outer interaction loop and an inner deliberation loop.

### Outer loop

```text
observe → deliberate → execute → record → observe ...
```

#### Observe

Receive the raw grid, legal actions, and current environment status. Any object-level description is a hypothesis constructed by the agent, not ground truth supplied by ARC.

#### Deliberate

Run an open-ended reasoning episode. During this phase the model may inspect history, edit the world model, backtest it, run search, and update durable notes. Deliberation ends only when the model commits a queue of real actions.

#### Execute

Apply the committed queue one action at a time. After each action, compare the observed transition with the transition predicted by the current world model.

#### Record

Append the real transition to an immutable Timeline. The model may revise notes and code, but it cannot rewrite the observations it received or the actions it actually took.

### Inner deliberation loop

```text
theorize → certify → plan → commit
     ↑         |
     └─ mismatch
```

#### Theorize: `write_code`

Edit the executable theory of the game, including state extraction and `step(state, action)` behavior. The world model is working scientific code, not merely prose in the context window.

#### Certify: `run_backtest`

Replay the candidate world model against every recorded transition. Certification requires exact agreement with the complete Timeline. A mismatch is returned as a focused counterexample that points to a bug in either the representation or the mechanism.

"Certified" here means consistent with the recorded history. It does not prove that the model is the unique or true mechanism. Multiple hypotheses may still agree on every transition seen so far.

#### Plan: `run_bfs`

Once the model reproduces the history, search inside it. Breadth-first search can explore thousands of modeled states without consuming an environment action. Search is free with respect to RHAE because only interactions with the real game are scored.

#### Commit: `commit_actions`

This is the only route from internal reasoning to external action. The separation prevents arbitrary analysis code from silently modifying the environment and makes each real action attributable to an explicit committed plan.

### Surprise invalidates the remaining plan

Reality always outranks the simulator. If any observed transition disagrees with the prediction, Schema immediately discards the unexecuted remainder of the action queue and returns to deliberation. The failed transition is appended to the Timeline and becomes a new counterexample. The model must account for it before normal planning resumes.

This protocol avoids continuing a long plan after its premises have become false.

## Durable memory

The diagram presents three persistent artifacts as the effective learned state of the agent:

- `world_model.py`: the executable representation, transition model, and goal logic;
- `notes.md`: explicit working knowledge, uncertainties, confirmed mechanics, and plans;
- an append-only Timeline: the authoritative history of observations and actions.

The Timeline survives bounded working memory and context compaction. A model cannot safely rely on remembered summaries when exact transitions matter. It can instead rerun its current theory over the full record.

The article's LS20 example illustrates the cycle:

1. The model grounds a plus-shaped sprite, a cyan/maroon block, a framed glyph, and a colored bar.
2. It hypothesizes that the block is the avatar and that the bar tracks a move budget.
3. A world-model revision reproduces all 36 recorded transitions.
4. It commits a six-action plan.
5. One action causes 77 cells to differ from the prediction because the block also repaints an indicator.
6. Schema stops the rest of the plan, records the surprise, adds the repaint rule, backtests again, and searches for a new shortest plan.
7. The resulting model transfers across seven levels, using 642 actions against a 780-action human baseline and obtaining a game RHAE of 100.

## Actions as experiments

When several hypotheses remain consistent with history, Schema should not select an arbitrary one and continue. It should seek a discriminating experiment: an action for which the candidate models predict different next observations.

The best probe has high expected information value and low environment cost. Because all probes count against RHAE, experimental design is part of planning rather than a separate academic exercise.

This leads to a practical scientific loop:

```text
maintain competing hypotheses
        ↓
find a state/action where predictions diverge
        ↓
commit the smallest useful experiment
        ↓
observe the real transition
        ↓
eliminate or revise hypotheses
        ↓
backtest against all accumulated evidence
```

## What the reported numbers mean

### Fixed fallback protocol

The reported pairings use a fixed rerun rule:

- Opus 4.8 runs first for the Claude pairing. Games below 80 are rerun with Fable 5, and the higher game score is retained.
- Sol xhigh runs first for the GPT pairing. Games below 80 are rerun with Sol max, and the higher game score is retained.

For the retained Claude results, 14 games use Opus and 11 use Fable. Nineteen of the 25 retained games score exactly 100; the remaining six range from 89.87 to 99.10. The median is 100.

For the retained Sol results, 15 games use xhigh and 10 use max. Twenty games score exactly 100; the remaining five range from 60.93 to 87.80. The median is also 100.

### Controlled and contextual comparisons

The controlled Claude comparison keeps the Opus/Fable model pairing fixed and changes the process around it:

```text
Claude Code scratch snapshot: 42.83%
Schema:                       98.98%
Difference:                  +56.15 percentage points
```

The article attributes this difference to three enforced constraints:

1. the current theory must exist as runnable `step()` code;
2. the code must be checked against every recorded transition before planning;
3. actions must pass through `commit_actions`, with the rest of a plan canceled after a prediction error.

The Sol comparison is contextual rather than controlled. Schema's xhigh/max pairing scores 95.35%, while the official 13.33% reference is the best individual Sol max Public result, not the same model pairing under a different harness.

### Evaluation limitations

The article makes several explicit qualifications:

- Both Schema scores are self-reported.
- The released artifacts cover the 25 Public games.
- The article does not claim a frozen-harness held-out evaluation.
- A near-ceiling Public result cannot be numerically extrapolated to Semi-private.
- The Public-to-Semi-private relationship remains unknown until directly measured.

## Case studies: what an executable model buys

### Observation 1: correct world programs reduce real actions

In 14 of 25 games where the agent induced a program that exactly reproduced the recorded history, it reportedly used 1.6–5.0 times fewer actions than the human reference. The article attributes the gain to two mechanisms.

First, complete-history verification makes accumulated evidence reusable. The model does not have to retest old facts after context compaction.

Second, planning occurs inside the simulator. Once `step()` and `is_goal()` are sufficiently accurate, BFS can examine roughly 10³–10⁴ modeled states without paying real actions. The same code can then be reused on later levels.

#### WA30: representation change creates the efficiency pivot

During Levels 2–4, the agent models a block as something directly steered. The model repeatedly fails, and the agent spends at least as many actions as the first-time human.

At the transition from Level 4 to Level 5, it changes the representation. The block is instead modeled as moving when the avatar's carry state changes. This sharply reduces mispredictions and transfers to later levels.

The article highlights:

- Level 2: 197 agent actions versus 119 human actions while the model is wrong.
- Level 8: 112 agent actions versus 442 human actions after correction; a verified 94-action plan is committed at once.
- Level 9: 70 agent actions versus 415 human actions.

The lesson is not that planning alone saves actions. Planning becomes useful only after the representation supports the right transition law.

#### RE86: one certified plan executes to completion

The final-level playback shows `run_backtest` replaying all recorded transitions, followed by a single 61-action plan that reaches a win with zero mispredictions. This is the cleanest example of discovery cost being paid before execution rather than during it.

#### KA59: exact memory kills an epicycle

Transitions across two complete runs show that an apparently successful rule only fit by coincidence. The agent deliberately chooses probes expected to produce informative mispredictions, then revises the model when the rule fails. The important capability is not remembering a verbal conclusion; it is retaining enough exact evidence to reject a convenient but false rule.

#### M0R0: search inside the model

Once the model is exact on history, BFS returns a 19-step solution for Level 4. The complete level uses 42 real actions, compared with a 500-action human baseline. The additional actions beyond the final plan are the cost of reaching and certifying the useful model.

### Observation 2: model quality changes discovery cost

The article compares Opus 4.8 Max and Fable 5 under the same executable harness. Both can eventually encode many of the same mechanisms. Their efficiency differs in how quickly they question the right assumption and choose an experiment that exposes the missing variable or transition.

Fable is described as more likely to:

- question the current representation after a contradiction;
- identify the uncertainty that blocks progress;
- choose an action whose outcomes separate competing theories;
- convert the result promptly into reusable code.

Opus often reaches the same mechanism, but after more actions spent exploring alternatives inside the existing representation.

#### FT09: hidden affordance versus prolonged target repair

The board appears to satisfy the current target logic but does not advance. Fable tests whether a checker-like element, previously treated as decoration, is itself actionable. The probe reveals a Lights Out-style cross operation that flips the selected cell and its orthogonal neighbors. Fable codes the rule, clears 11 actions later, and solves the next level in 13.

Opus continues revising target-state explanations for roughly 240 more actions. At step 287 it finally probes the checker, discovers the same affordance, and reaches an exact 270/270-transition backtest. The final expressive capability is similar; the experimental path is not.

#### DC22: exhaustive search of an incomplete graph

Opus builds a detailed model of movement and three toggles. From reset, BFS exhausts every state reachable under that model and correctly concludes that its target is unreachable. Fable exposes a portal transition that was absent from the graph and clears the level.

Search was correct relative to the model. The model was incomplete relative to the world.

#### LF52: composition appears only at exact geometry

Both models identify peg-solitaire behavior and a cart moving on tracks. The missing rule concerns how those mechanisms compose. Fable drives the cart to an exact docking coordinate and treats that configuration as an observation point. Opus leaves the decisive composition untested much longer.

This case shows that mechanisms may be understood individually while their interaction remains absent from the model.

#### SB26: reusable abstraction versus descriptive insight

Both models infer a DFS-like rule and eventually solve all eight levels. Fable preserves the rule as a reusable coded abstraction and applies it to Level 2 in about 15 actions. Opus later grinds through Level 6 before recovering a missing tile-shape variable.

There is a practical difference between naming a general idea and maintaining an implementation whose parameters absorb later variation.

## Article conclusion

The article presents Schema as the combination of three capabilities that were already emerging separately:

- frontier models that can adapt to unfamiliar environments;
- coding-agent infrastructure with tools and durable workspaces;
- executable programmatic world models.

Its broader ambition is mechanism discovery beyond ARC: grounding causal structure through repeated action and perception in environments richer than a small symbolic grid.

## Textual reconstruction of the figures

1. **Benchmark timeline:** ARC-AGI-3 results from launch through July 2026, separating verified and self-reported scores and Public versus Semi-private evaluations. Schema's two self-reported results are highlighted near 99% and 95.35%.
2. **Two abstraction levels:** state grounding maps observations to a state program; mechanism discovery maps `(state, action, next_state)` evidence to a transition program. Schema edits both in one program.
3. **Control loop:** observe, deliberate, execute, and record surround an append-only Timeline. Deliberation contains theorize, backtest, BFS, and commit. Persistent artifacts are the world model, notes, and Timeline. A surprise cancels the remaining plan.
4. **RHAE example:** an agent completing 7/7 levels near the 776-action human budget scores 97.7%; an agent spending 1,591 actions and stalling at 6/7 scores below 14%.
5. **Harness comparison:** Claude Code at 42.83% versus Schema at 98.98% is controlled for the Opus/Fable pairing. The Sol comparison is explicitly labeled contextual.
6. **All-game curves:** cumulative actions versus levels cleared for all 25 Public games, with toggles for Claude and Sol pairings against fixed human curves.
7. **WA30 crossover:** agent actions are near or above human actions before the L4→L5 model correction and far below human actions afterward.
8. **WA30 before pivot:** trial-heavy Level 2 under the incorrect block model.
9. **WA30 after pivot:** Level 8 executes a verified 94-action plan using the corrected model.
10. **RE86:** a 61-action final plan reaches a win with no mispredictions.
11. **KA59:** discriminating probes eliminate an epicycle rule.
12. **M0R0:** a green backtest and BFS yield a 19-step plan for a level humans solved in 500 actions.
13. **FT09:** Fable and Opus discover the same hidden checker action through very different experimental paths.
14. **DC22:** Fable reveals a portal edge missing from Opus's exhaustively searched graph.
15. **LF52:** exact cart docking exposes a cross-mechanism rule.
16. **SB26:** a reusable DFS abstraction transfers more efficiently than an incompletely parameterized one.

## Reverse-engineering synthesis for our future harness

This section is our interpretation of the article together with the downloaded traces. It is not a claim that every internal implementation detail below was stated by the authors.

### The harness is a protocol, not the solver

Schema does not appear to hard-code solutions for the 25 games. Its main contribution is forcing the model's reasoning into an auditable scientific protocol:

```text
raw observation
    ↓
explicit state hypothesis + executable dynamics
    ↓
complete-history consistency check
    ↓
model-space planning or discriminating experiment
    ↓
explicit action commitment
    ↓
per-action prediction check
    ↓
append-only evidence and possible revision
```

The language model remains responsible for inventing objects, hidden variables, transition rules, goal conditions, and useful experiments. The harness makes those inventions persistent, testable, searchable, and unable to silently bypass reality.

### Likely minimal components

#### 1. Environment adapter

Owns the actual ARC session. It exposes the current grid, legal actions, status, level, and action budget. It is the only component allowed to mutate the game.

#### 2. Immutable transition Timeline

Stores every pre-state, action, post-state, and terminal signal in order. This is the evidentiary base for backtesting and score reconstruction.

#### 3. Editable world-model workspace

Holds the model-generated decoder, state, transition function, goal predicate, helper code, and durable notes. Multiple revisions can coexist as candidate files during investigation.

#### 4. Deterministic backtester

Loads a candidate world model and replays all applicable Timeline transitions. A useful report must identify the earliest mismatch and distinguish state-decoding errors from transition-prediction errors where possible.

#### 5. Model-space planner

Searches only a certified candidate model. BFS is the default described in the article, but the interface should allow other planners when state spaces are large. Search returns a plan plus evidence that the modeled goal was reached.

#### 6. Transactional action committer

Accepts an explicit finite queue, records its rationale, and executes one action at a time. It predicts before each step, compares after each step, and aborts the remaining queue on the first discrepancy.

#### 7. Scoring and budget monitor

Tracks real actions, level completions, human baselines, and RHAE consequences. This lets the reasoning process trade off information gain against interaction cost.

### The trace archive matches this decomposition

The downloaded trajectories contain concrete counterparts of the article's conceptual artifacts:

- `events.jsonl` behaves as the append-only Timeline.
- `run.json` records run-level configuration and provenance.
- `notes.md` contains durable hypotheses, confirmed mechanics, uncertainty, and plans.
- files such as `world_model_v5.py` and candidate scripts preserve executable theories and revisions.
- `evaluation_results.csv` and `baseline_actions.csv` support score reconstruction.
- snapshots and shareable text/image artifacts preserve what the model and evaluator observed.

The event stream exposes a transactional sequence resembling:

```text
turn_started
tool_started(commit_actions)
tool_finished
turn_committed
action_taken
next turn_started
```

This is useful because the article explains intent while the traces reveal the operational contract.

### Schemas we will eventually need

Without implementing them yet, the conceptual data contracts are:

- **Observation:** raw grid, legal actions, level, terminal state, action index.
- **TransitionRecord:** pre-observation, committed action, post-observation, prediction, mismatch summary.
- **WorldModelRevision:** code artifact, parent revision, claimed change, backtest status.
- **BacktestReport:** transitions checked, exact matches, earliest counterexample, mismatch magnitude.
- **Hypothesis:** uncertain mechanism, predicted alternatives, evidence for and against.
- **Experiment:** proposed action, competing predictions, expected information gain, real-action cost.
- **Plan:** model revision used, initial modeled state, action queue, modeled terminal state.
- **CommitResult:** executed prefix, observed transitions, aborted suffix, surprise/counterexample.
- **Scorecard:** per-level action counts, human baselines, completion cap, aggregate RHAE.

Pydantic can enforce these interfaces, while the game-specific state and transition program remain open-ended Python generated by the reasoning model.

### Non-negotiable invariants

The article suggests several invariants more important than any particular prompt:

1. No environment mutation occurs outside the commit channel.
2. Every real action and observation is appended before further deliberation.
3. Recorded history is never rewritten to agree with a hypothesis.
4. A model revision is not trusted for planning until it passes backtesting.
5. Passing backtesting means historical consistency, not truth or uniqueness.
6. A prediction error invalidates the remaining committed plan immediately.
7. Search results are labeled with the exact world-model revision that produced them.
8. Reset and undo are ordinary environment actions unless the benchmark specifies otherwise; their costs and state semantics must be learned and logged.
9. Hidden state may persist even when the rendered grid is identical.
10. Search completeness is always relative to the representation and transition graph.

### The deepest design lesson

The hard problem is not simply generating a better action. It is maintaining the boundary between three kinds of truth:

- **Observed truth:** immutable transitions from the real environment.
- **Modeled truth:** what the current executable theory predicts.
- **Planning truth:** what follows if the modeled theory is assumed.

Many agent failures occur when these layers blur: a verbal guess is remembered as an observation, a backtest-fitting epicycle is treated as the true rule, or an exhaustive search over an incomplete graph is interpreted as proof that the real task is impossible.

Schema's architecture is valuable because it keeps the layers separate and makes every crossing explicit. That separation—more than BFS, any single model, or a particular prompt—is the part our ARC-AGI-3 harness should reproduce.

## References

- [Original Schema article](https://schema-harness.github.io/)
- [Released Schema gameplay traces](https://huggingface.co/datasets/schema-harness/arc-agi-3-schema-traces)
- [Local trace archive](../arc-agi-3-schema-traces/README.md)
- [ARC-AGI-3 technical report](https://arcprize.org/media/ARC_AGI_3_Technical_Report.pdf)
- [ARC-AGI-3 launch article](https://arcprize.org/blog/arc-agi-3-launch)
- [Official GPT-5.6 Sol result](https://arcprize.org/results/openai-gpt-5-6)
- [VIGA project](https://fugtemypt123.github.io/VIGA-website/)
- [WorldCoder paper](https://arxiv.org/abs/2402.12275)
