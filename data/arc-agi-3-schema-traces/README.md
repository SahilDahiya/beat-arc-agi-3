# ARC-AGI-3 Schema Gameplay Trajectories

This release contains 50 ARC-AGI-3 gameplay trajectories and a dependency-free
scoring utility. The trajectories are split evenly across two collections:

- `gpt_5_6_sol/`: 25 GPT-5.6 Sol trajectories.
- `claude_fable_opus/`: 25 trajectories from Claude Opus 4.8 and Claude Fable 5.

Each trajectory directory includes `run.json`, a streamed `events.jsonl` event
log, sanitized session data, snapshots, and the shareable text/image files
produced during the run.

## Layout

```text
arc-agi-3-schema-gameplay/
├── README.md
├── score_trajectories.py
├── gpt_5_6_sol/
│   ├── baseline_actions.csv
│   ├── evaluation_results.csv
│   └── <25 trajectory directories>/
└── claude_fable_opus/
    ├── evaluation_results.csv
    └── <25 trajectory directories>/
```

`baseline_actions.csv` contains the human action baselines shared by both
collections. Each `evaluation_results.csv` is a compact manifest of the
corresponding 25 trajectories.

## Recompute all scores

Python 3.10 or newer is recommended. The scorer uses only the Python standard
library, so no packages need to be installed.

From this directory, run:

```bash
python3 score_trajectories.py
```

The command discovers all trajectory directories, streams all 50
`events.jsonl` files, reconstructs per-level action counts, recomputes every
RHAE score, and prints one 50-row table followed by a summary table. By default
it also verifies that the event-derived actions and scores match both
`evaluation_results.csv` manifests.

Useful options:

```bash
# Narrower terminal output
python3 score_trajectories.py --compact

# Score a copy located elsewhere
python3 score_trajectories.py --root ~/agent-dataset/arc-agi-3-schema-gameplay

# Allow a trajectory count other than 50
python3 score_trajectories.py --expected 0

# Recompute from events without checking the CSV manifests
python3 score_trajectories.py --no-manifest-check
```

The default command exits nonzero if a log is malformed, an action sequence is
not contiguous, a baseline is missing, the collection does not contain exactly
25+25 trajectories, or a recomputed result differs from a manifest.

## Scoring

For completed level `i`, with human baseline actions `h_i` and trajectory
actions `a_i`, the per-level score is:

```text
level_score_i = min(115, 100 * (h_i / a_i)^2)
```

Incomplete or missing levels receive zero. The raw game score is the weighted
mean of the level scores, using the one-based level number as its weight. A
completion cap prevents unfinished games from receiving more credit than the
weighted share of levels they completed:

```text
raw_game_score = weighted_mean(level_score_i, weight=i)
completion_cap = 100 * sum(i for completed levels) / sum(i for all levels)
RHAE           = min(raw_game_score, completion_cap)
```

The 115% per-level cap permits a more action-efficient trajectory to offset a
less efficient level, while the final game score remains capped at 100%.

In the terminal table, `Level actions` lists only completed-level action counts
in order.

## Verified release summary

Running the scorer on the included data produces:

| Collection | Trajectories | Wins | Levels | Mean RHAE |
|---|---:|---:|---:|---:|
| `gpt_5_6_sol` | 25 | 24 | 182/183 | 95.35% |
| `claude_fable_opus` | 25 | 25 | 183/183 | 98.98% |
