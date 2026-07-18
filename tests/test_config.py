from pydantic import SecretStr

from beat_arc_agi_3.config import Settings


def test_settings_accept_explicit_runtime_configuration() -> None:
    settings = Settings(
        arc_api_key=SecretStr("arc-test"),
        openai_api_key=SecretStr("openai-test"),
        pydantic_ai_model="openai:test-model",
    )

    assert settings.arc_api_key.get_secret_value() == "arc-test"
    assert settings.pydantic_ai_model == "openai:test-model"
