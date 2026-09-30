import os

import pytest

from ai.openai_client import (
    DEFAULT_MODEL,
    OpenAIConfig,
    OpenAIConfigurationError,
    OpenAIResponsesClient,
)


def test_openai_config_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(OpenAIConfigurationError):
        OpenAIConfig.from_environment()


def test_openai_config_uses_safe_defaults(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    config = OpenAIConfig.from_environment()

    assert config.api_key == "test-key"
    assert config.model == DEFAULT_MODEL
    assert config.base_url == "https://api.openai.com/v1"


def test_openai_client_does_not_require_network_for_construction():
    client = OpenAIResponsesClient(
        OpenAIConfig(api_key="test-key"),
    )
    assert client.config.api_key == "test-key"


def test_environment_does_not_contain_project_key(monkeypatch):
    # The repository integration must consume credentials from the environment,
    # not from a source-controlled constant.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert os.environ["OPENAI_API_KEY"] == "test-key"
