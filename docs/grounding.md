# Pydantic AI grounding

read_when: you are designing or implementing a Pydantic AI agent, tool, dependency, output, or test

Implementation targets the installed Pydantic AI 2.12 API and is grounded in the official documentation:

- [Dependencies](https://ai.pydantic.dev/dependencies/): typed runtime dependencies are accessed through `RunContext` in tools and output validators.
- [Function tools](https://ai.pydantic.dev/tools/): `@agent.tool` is used when a tool requires `RunContext`.
- [Output](https://ai.pydantic.dev/output/): `ToolOutput` provides a named structured output tool. `end_strategy="early"` skips function tools emitted alongside a successful final output.
- [Testing](https://ai.pydantic.dev/testing/): `FunctionModel` provides deterministic unit tests without real model requests.
- [Usage limits](https://ai.pydantic.dev/agent/#usage-limits): `UsageLimits` defaults to a 50-request cap; setting its fields to `None` disables SDK enforcement.
- [OpenAI provider](https://ai.pydantic.dev/models/openai/): an explicit `OpenAIProvider` can receive a preconfigured `AsyncOpenAI` client and be passed to `OpenAIResponsesModel`.
- [GPT-5.5](https://developers.openai.com/api/docs/models/gpt-5.5): the requested API model ID is `gpt-5.5` and it supports structured output and function calling.
- [Pydantic Evals overview](https://pydantic.dev/docs/ai/evals/evals/): code-first datasets organize cases and evaluators and produce evaluation reports.
- [Pydantic Evals custom evaluators](https://pydantic.dev/docs/ai/evals/evaluators/custom/): deterministic evaluators can return named assertions with reasons.
- [Pydantic Evals multi-run evaluation](https://pydantic.dev/docs/ai/evals/how-to/multi-run/): repeated case execution measures stochastic systems.
- [Pydantic Evals concurrency](https://pydantic.dev/docs/ai/evals/how-to/concurrency/): case concurrency is explicit and can be restricted for resource-bound tasks.

Current decisions:

- Register `CommitActions` as `ToolOutput(..., name="commit_actions")`.
- Use `end_strategy="early"` because committing must terminate the turn before any sibling function tool runs.
- Use an output validator with `RunContext[AgentDeps]` for current-frame legal-action validation.
- Use `FunctionModel` and disable real model requests in agent tests.
- Pass an explicit all-`None` `UsageLimits` value during deliberation. Request, tool-call, token, and time policy belongs to the harness rather than Pydantic AI.
- Configure `openai-codex:gpt-5.5`, explicitly construct `OpenAIResponsesModel` from `Settings` and harness-owned subscription credentials with `build_openai_model`, and pass that model to `build_agent`. A missing model or OAuth login fails immediately; neither triggers implicit provider configuration.
- Use the direct OAuth/backend pattern studied in JACA: the harness performs PKCE login, stores and refreshes its own credentials, and configures a dedicated OpenAI client for the ChatGPT Codex backend. This is an implementation-specific subscription integration, not the standard OpenAI Platform API-key path.
- Preserve JACA's streamed-request behavior at the model boundary. The ChatGPT Codex backend rejects non-streaming requests, so `OpenAICodexResponsesModel.request` directly opens and drains `request_stream`; the outer agent loop remains transport-agnostic. The public Responses API likewise defines `stream=true` as its SSE streaming mode.
- Use code-first Pydantic Evals `Dataset` objects for immutable Session-evidence regression and ad hoc stage-outcome scoring. Deterministic custom evaluators compare declared fixture facts or observable target success, while task-recorded metrics remain diagnostic. Run persisted Session cases with `max_concurrency=1`; reserve repeated execution for future fresh live runs.
