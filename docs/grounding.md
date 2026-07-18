# Pydantic AI grounding

read_when: you are designing or implementing a Pydantic AI agent, tool, dependency, output, or test

Implementation targets the installed Pydantic AI 2.12 API and is grounded in the official documentation:

- [Dependencies](https://ai.pydantic.dev/dependencies/): typed runtime dependencies are accessed through `RunContext` in tools and output validators.
- [Function tools](https://ai.pydantic.dev/tools/): `@agent.tool` is used when a tool requires `RunContext`.
- [Output](https://ai.pydantic.dev/output/): `ToolOutput` provides a named structured output tool. `end_strategy="early"` skips function tools emitted alongside a successful final output.
- [Testing](https://ai.pydantic.dev/testing/): `FunctionModel` provides deterministic unit tests without real model requests.
- [OpenAI provider](https://ai.pydantic.dev/models/openai/): an explicit `OpenAIProvider` can receive an API key in code and be passed to `OpenAIResponsesModel`.
- [GPT-5.5](https://developers.openai.com/api/docs/models/gpt-5.5): the requested API model ID is `gpt-5.5` and it supports structured output and function calling.

Current decisions:

- Register `CommitActions` as `ToolOutput(..., name="commit_actions")`.
- Use `end_strategy="early"` because committing must terminate the turn before any sibling function tool runs.
- Use an output validator with `RunContext[AgentDeps]` for current-frame legal-action validation.
- Use `FunctionModel` and disable real model requests in agent tests.
- Configure `openai:gpt-5.5`, explicitly construct `OpenAIResponsesModel` from `Settings` with `build_openai_model`, and pass that model to `build_agent`. A missing model fails immediately; it never triggers implicit configuration loading.
