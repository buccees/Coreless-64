from ai.registry import AICoreRegistry
from ai.interfaces import AIRequest, AIResult
from vigil.ai import CorelessVigilAI
from vigil.interaction import InputModality, InteractionRequest
from vigil.runtime import VigilEnvironment
from vigil.security import AuthorizationContext, AuthorizationService


class RecordingCore:
    model_id = "shared-core"
    def __init__(self):
        self.requests = []
    def infer(self, request: AIRequest) -> AIResult:
        self.requests.append(request)
        return AIResult(request.request_id, self.model_id, "The target is present.")


def test_runtime_interaction_uses_shared_coreless_ai_and_returns_grounding():
    core = RecordingCore()
    registry = AICoreRegistry()
    registry.register(core)
    env = VigilEnvironment(enabled=True, ai_registry=registry)
    request = InteractionRequest(
        "req-1", InputModality.TEXT, "What is present?", 10, "session-1", "vigil.read"
    )
    response = env.handle_interaction(request, required_scope="vigil.read")
    assert response is not None
    assert response.grounded
    assert response.text == "The target is present."
    assert response.request_id == "req-1"
    assert len(core.requests) == 1


def test_runtime_interaction_requires_authorization_scope():
    env = VigilEnvironment(enabled=True)
    request = InteractionRequest(
        "req-2", InputModality.TEXT, "Hello", 10, "session-1", "vigil.read"
    )
    try:
        env.handle_interaction(request, required_scope="vigil.write")
    except PermissionError:
        pass
    else:
        raise AssertionError("expected authorization failure")


def test_authorization_service_keeps_scope_check_deterministic():
    service = AuthorizationService()
    assert service.authorize(AuthorizationContext("s", frozenset({"vigil.read"})), "vigil.read")
    assert not service.authorize(AuthorizationContext("s", frozenset({"vigil.read"})), "vigil.write")
