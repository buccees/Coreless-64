from ai.interfaces import AIRequest, AIResult
from ai.registry import AICoreRegistry


class FakeCore:
    def __init__(self, model_id: str):
        self._model_id = model_id

    @property
    def model_id(self) -> str:
        return self._model_id

    def infer(self, request: AIRequest) -> AIResult:
        return AIResult(request.request_id, self._model_id, "ok")


def test_registry_registers_and_invokes_enabled_cores():
    registry = AICoreRegistry()
    registry.register(FakeCore("qwen3"))
    registry.register(FakeCore("deepseek"))

    results = registry.infer(AIRequest("r1", "analyze"))

    assert tuple(r.model_id for r in results) == ("qwen3", "deepseek")


def test_registry_can_disable_a_core_without_removing_it():
    registry = AICoreRegistry()
    registry.register(FakeCore("gpt-oss"))
    registry.set_enabled("gpt-oss", False)

    assert registry.enabled_cores() == ()
    assert registry.descriptor("gpt-oss").enabled is False


def test_registry_rejects_duplicate_model_ids():
    registry = AICoreRegistry()
    registry.register(FakeCore("gemma"))

    try:
        registry.register(FakeCore("gemma"))
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate model ID was accepted")


def test_registry_rejects_inference_from_disabled_core():
    registry = AICoreRegistry()
    registry.register(FakeCore("codestral"), enabled=False)

    try:
        registry.infer(AIRequest("r1", "analyze"))
    except RuntimeError:
        pass
    else:
        raise AssertionError("disabled core was invoked")
