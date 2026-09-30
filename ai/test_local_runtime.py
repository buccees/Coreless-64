import json
from unittest.mock import patch

from ai.interfaces import AIRequest
from ai.local_runtime import (
    LocalModelSpec,
    LocalOpenAICompatibleCore,
    build_default_local_cores,
    register_default_local_cores,
)


def test_local_core_uses_common_ai_core_contract():
    core = LocalOpenAICompatibleCore(
        LocalModelSpec("qwen3", "qwen3", endpoint="http://local.test/v1")
    )
    assert core.model_id == "qwen3"


def test_local_core_posts_prompt_and_returns_ai_result():
    response = {
        "choices": [
            {"message": {"role": "assistant", "content": "local result"}}
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(response).encode()

    with patch("urllib.request.urlopen", return_value=FakeResponse()) as opened:
        result = LocalOpenAICompatibleCore(
            LocalModelSpec("deepseek", "deepseek", endpoint="http://local.test/v1")
        ).infer(AIRequest("r1", "inspect", {"cpu": 2}))

    assert result.model_id == "deepseek"
    assert result.text == "local result"
    request = opened.call_args.args[0]
    payload = json.loads(request.data.decode())
    assert payload["model"] == "deepseek"
    assert payload["messages"][1]["role"] == "user"


def test_default_local_factory_builds_all_selected_cores_without_network():
    cores = build_default_local_cores(endpoint="http://local.test/v1")
    assert tuple(core.model_id for core in cores) == (
        "qwen3",
        "deepseek",
        "gpt-oss",
        "gemma",
        "codestral",
    )
\n\ndef test_default_local_cores_register_with_common_registry():\n    from ai.registry import AICoreRegistry\n\n    registry = AICoreRegistry()\n    ids = register_default_local_cores(registry, endpoint="http://local.test/v1")\n    assert ids == ("qwen3", "deepseek", "gpt-oss", "gemma", "codestral")\n    assert registry.enabled_cores() == ids\n

def test_all_five_local_cores_can_enter_314dnest_together():
    from ai.coordinator import NestCoordinator
    from ai.registry import AICoreRegistry

    response = {
        "choices": [
            {"message": {"role": "assistant", "content": "local analysis"}}
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(response).encode()

    registry = AICoreRegistry()
    register_default_local_cores(registry, endpoint="http://local.test/v1")

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = NestCoordinator(registry).coordinate(
            AIRequest("group-1", "analyze", {"source": "coreless"})
        )

    assert tuple(item.model_id for item in result.results) == (
        "qwen3", "deepseek", "gpt-oss", "gemma", "codestral"
    )
    assert result.failures == ()
    assert result.group.participants == (
        "qwen3", "deepseek", "gpt-oss", "gemma", "codestral"
    )
