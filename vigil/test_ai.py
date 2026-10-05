from ai.interfaces import AIRequest, AIResult
from ai.registry import AICoreRegistry
from vigil.ai import CorelessVigilAI
from vigil.model import EntityType, Uncertainty, WorldEntity


class RecordingCore:
    model_id = "test-core"

    def __init__(self):
        self.requests = []

    def infer(self, request: AIRequest) -> AIResult:
        self.requests.append(request)
        return AIResult(request_id=request.request_id, model_id=self.model_id, text="grounded analysis")


def test_vigil_uses_existing_coreless_ai_registry():
    core = RecordingCore()
    registry = AICoreRegistry()
    registry.register(core)
    entity = WorldEntity(entity_id="entity-1", entity_type=EntityType.OBJECT, label="camera", position=(1.0, 2.0, 3.0), track_id=None, confidence=1.0, uncertainty=Uncertainty(), provenance=(), first_seen_ns=1, last_seen_ns=1)
    bridge = CorelessVigilAI(registry)
    result = bridge.analyze("What is present?", (entity,), request_id="req-1")
    assert result is not None
    assert result.model_id == "test-core"
    assert result.grounded_entity_ids == ("entity-1",)
    assert len(core.requests) == 1
    assert core.requests[0].request_id == "req-1"
    assert core.requests[0].context["source"] == "vigil"


def test_vigil_ai_is_unavailable_without_coreless_registry():
    bridge = CorelessVigilAI()
    assert not bridge.available()
    assert bridge.analyze("Anything?", ()) is None
