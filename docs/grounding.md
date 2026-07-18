# Pydantic AI grounding

read_when: you are designing or implementing a Pydantic AI agent, tool, dependency, output, or test

Implementation targets the installed Pydantic AI 2.12 API and is grounded in the official documentation:

- [Dependencies](https://ai.pydantic.dev/dependencies/): typed runtime dependencies are accessed through `RunContext` in tools and output validators.
- [Function tools](https://ai.pydantic.dev/tools/): `@agent.tool` is used when a tool requires `RunContext`.
- [Output](https://ai.pydantic.dev/output/): `ToolOutput` provides a named structured output tool. `end_strategy="early"` skips function tools emitted alongside a successful final output.
- [Testing](https://ai.pydantic.dev/testing/): `FunctionModel` provides deterministic unit tests without real model requests.

Current decisions:

- Register `CommitActions` as `ToolOutput(..., name="commit_actions")`.
- Use `end_strategy="early"` because committing must terminate the turn before any sibling function tool runs.
- Use an output validator with `RunContext[AgentDeps]` for current-frame legal-action validation.
- Use `FunctionModel` and disable real model requests in agent tests.
