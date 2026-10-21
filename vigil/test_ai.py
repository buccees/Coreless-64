from ai.interfaces import AIRequest, AIResult
from ai.registry import AICoreRegistry
from vigil.ai import CorelessVigilAI
from vigil.model import EntityType, Uncertainty, WorldEntity


class RecordingCore:
    def __init__(self, model_id="qwen3", text="grounded analysis"):
        self.model_id = model_id
        self.text = text
        self.requests = []

    def infer(self, request: AIRequest) -> AIResult:
        self.requests.append(request)
        return AIResult(request_id=request.request_id, model_id=self.model_id, text=self.text)


class BrokenCore(RecordingCore):
    def infer(self, request: AIRequest) -> AIResult:
        raise RuntimeError("shared model unavailable")


def sample_entity():
    return WorldEntity(
        entity_id="entity-1",
        entity_type=EntityType.OBJECT,
        label="camera",
        position=(1.0, 2.0, 3.0),
        track_id=None,
        confidence=1.0,
        uncertainty=Uncertainty(),
        provenance=(),
        first_seen_ns=1,
        last_seen_ns=1,
    )


def test_vigil_uses_shared_qwen3_from_existing_coreless_registry():
    qwen3 = RecordingCore("qwen3")
    unrelated = RecordingCore("deepseek")
    registry = AICoreRegistry()
    registry.register(qwen3)
    registry.register(unrelated)

    bridge = CorelessVigilAI(registry)
    result = bridge.analyze("What is present?", (sample_entity(),), request_id="req-1")

    assert result is not None
    assert result.model_id == "qwen3"
    assert result.grounded_entity_ids == ("entity-1",)
    assert len(qwen3.requests) == 1
    assert unrelated.requests == []
    assert qwen3.requests[0].request_id == "req-1"
    assert qwen3.requests[0].context["source"] == "vigil"
    assert qwen3.requests[0].context["task_kind"] == "EXPLAIN_RESULT"


def test_vigil_ai_is_unavailable_without_registered_qwen3():
    registry = AICoreRegistry()
    registry.register(RecordingCore("deepseek"))
    bridge = CorelessVigilAI(registry)
    assert not bridge.available()
    assert bridge.analyze("Anything?", ()) is None


def test_vigil_ai_degrades_when_shared_qwen3_is_unavailable():
    registry = AICoreRegistry()
    registry.register(BrokenCore())
    bridge = CorelessVigilAI(registry)
    assert bridge.available()
    assert bridge.analyze("Anything?", ()) is None


def test_vigil_ai_respects_disabled_shared_qwen3():
    registry = AICoreRegistry()
    registry.register(RecordingCore())
    registry.set_enabled("qwen3", False)
    bridge = CorelessVigilAI(registry)
    assert not bridge.available()
    assert bridge.analyze("Anything?", ()) is None
