import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pydantic_ai import ModelResponse, TextPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.providers.openai import OpenAIProvider

from beat_arc_agi_3.openai_codex_model import OpenAICodexResponsesModel


class RecordingStream:
    def __init__(self, response: ModelResponse) -> None:
        self.response = response
        self.drained = False

    async def __aiter__(self) -> AsyncIterator[object]:
        yield object()
        self.drained = True

    def get(self) -> ModelResponse:
        assert self.drained is True
        return self.response


def test_non_streaming_model_entrypoint_uses_and_drains_stream(
    monkeypatch,
) -> None:
    model = OpenAICodexResponsesModel(
        "gpt-5.5",
        provider=OpenAIProvider(api_key="unused-test-key"),
    )
    expected = ModelResponse(parts=[TextPart("complete")])
    stream = RecordingStream(expected)
    calls: list[tuple[object, object, object]] = []

    @asynccontextmanager
    async def request_stream(messages, settings, parameters):
        calls.append((messages, settings, parameters))
        yield stream

    monkeypatch.setattr(model, "request_stream", request_stream)
    parameters = ModelRequestParameters()

    response = asyncio.run(model.request([], None, parameters))

    assert response is expected
    assert calls == [([], None, parameters)]
