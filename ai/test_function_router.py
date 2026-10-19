from function_router import FunctionalModelRouter
from interfaces import AIResult
from registry import AICoreRegistry


class StubCore:
    def __init__(self, model_id):
        self.model_id = model_id

    def infer(self, request):
        return AIResult(request.request_id, self.model_id, "ok")


class MemoryStorage:
    def __init__(self):
        self.values = {}

    def put(self, key, value):
        self.values[key] = value

    def get(self, key):
        if key not in self.values:
            raise KeyError(key)
        return self.values[key]


def make_router():
    registry = AICoreRegistry()
    for model_id in ("qwen3", "codestral", "gemma"):
        registry.register(StubCore(model_id))
    return registry, FunctionalModelRouter(registry)


def test_function_router_selects_only_explicitly_assigned_models():
    registry, router = make_router()
    router.assign("code_generation", "codestral")
    router.assign("general_reasoning", "qwen3")
    router.assign("code_review", "codestral")
    assert router.models_for("code_generation") == ("codestral",)
    assert router.models_for("general_reasoning") == ("qwen3",)
    assert router.models_for("code_review") == ("codestral",)
    assert router.assignments() == {
        "code_generation": ("codestral",),
        "code_review": ("codestral",),
        "general_reasoning": ("qwen3",),
    }


def test_function_router_can_assign_multiple_models_in_declared_order():
    _, router = make_router()
    router.assign("analysis", "qwen3")
    router.assign("analysis", "gemma")
    router.assign("analysis", "qwen3")
    assert router.models_for("analysis") == ("qwen3", "gemma")


def test_function_router_skips_disabled_models_and_fails_closed():
    registry, router = make_router()
    router.assign("communication", "gemma")
    registry.set_enabled("gemma", False)
    try:
        router.models_for("communication")
    except LookupError as exc:
        assert "no enabled model" in str(exc)
    else:
        raise AssertionError("router selected a disabled model")


def test_function_router_persists_assignments_and_restores():
    registry, router = make_router()
    router.assign("code_generation", "codestral")
    router.assign("analysis", "qwen3")
    storage = MemoryStorage()
    router.save(storage)

    restored = FunctionalModelRouter(registry)
    restored.load(storage)
    assert restored.assignments() == {
        "analysis": ("qwen3",),
        "code_generation": ("codestral",),
    }


def test_function_router_rejects_unknown_models_and_empty_functions():
    _, router = make_router()
    try:
        router.assign("code_generation", "not-registered")
    except KeyError:
        pass
    else:
        raise AssertionError("unregistered model was assigned")
    try:
        router.assign(" ", "qwen3")
    except ValueError:
        pass
    else:
        raise AssertionError("empty function was accepted")
