# Project documentation

read_when: you need the canonical direction, architecture, contracts, or implementation grounding for this repository

- [Goal](goal.md): the current product boundary and milestone.
- [Architecture](architecture.md): ownership and control-flow boundaries.
- [Contracts](contracts.md): canonical Python types and invariants.
- [Configuration](configuration.md): required resources, current policy defaults, and the configurable process direction.
- [Grounding](grounding.md): source-backed Pydantic AI decisions.
- [Schema article synthesis](../data/schema-harness/article.md): the harness we are studying.
- [Trace tool analysis](../data/arc-agi-3-schema-traces/TRACE_TOOL_ANALYSIS.md): observed tool behavior in released traces.
- [Theoretical grounding](../data/schema-harness/theoretical-grounding.md): links between the traces and the MIT synthesis course.

## Tests

`uv run pytest` intentionally includes a required live integration test. It loads the repository `.env`, calls the configured model through the harness-owned ChatGPT subscription OAuth connection, creates a real online Arcade environment, and executes one real ARC action. Missing OAuth credentials, unavailable subscription model access, ARC service failures, and action failures fail the suite; there is no skip or fake fallback.

The harness executes generated Python through `bubblewrap`; `bwrap` must be installed and usable. There is no unsandboxed execution fallback.

## Run an agent session

Authenticate the harness once in a browser:

```bash
uv run python -m beat_arc_agi_3 auth login
uv run python -m beat_arc_agi_3 auth status
```

`auth login` prints an OpenAI authorization URL and waits for its loopback callback on `localhost:1455`. The harness stores the resulting credentials at `~/.beat-arc-agi-3/oauth.json`, refreshes expired access tokens when possible, and never reads `OPENAI_API_KEY`. Use `auth logout` to remove the stored credentials.

Every process value is explicit:

```bash
uv run python -m beat_arc_agi_3 run \
  --game ls20 \
  --session ls20-experiment-001 \
  --mode online \
  --max-turns 10 \
  --max-actions 30
```

The command uses ChatGPT subscription model access and performs real ARC actions. `--session` is a reusable label; each run prefixes it with a UTC timestamp and writes a distinct directory such as `sessions/20260718T153012.123456Z-ls20-experiment-001/`. Process resume is not implemented yet.
