from pydantic_ai import ModelMessage, ModelResponse
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.settings import ModelSettings


class OpenAICodexResponsesModel(OpenAIResponsesModel):
    """Responses model adapter for the streaming-only ChatGPT Codex backend."""

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        async with self.request_stream(
            messages,
            model_settings,
            model_request_parameters,
        ) as response_stream:
            async for _ in response_stream:
                pass
        return response_stream.get()
