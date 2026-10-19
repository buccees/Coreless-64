"""End-to-end checks for function-based routing through the persistent AI runtime."""
from ai.interfaces import AIResult
from ai.machine_runtime import PersistentAIRuntime


class _FunctionRoutingCore:
    def __init__(self, model_id):
        self.model_id = model_id

    def infer(self, request):
        return AIResult(request.request_id, self.model_id, f"result from {self.model_id}")


class _FunctionRoutingStorage:
    def __init__(self):
        self.objects = {}

    def put(self, key, value):
        self.objects[key] = value

    def get(self, key):
        if key not in self.objects:
            raise KeyError(key)
        return self.objects[key]


def test_function_routing_executes_only_the_assigned_enabled_model():
    runtime = PersistentAIRuntime(_FunctionRoutingStorage(), local_cores=False)
    runtime.registry.register(_FunctionRoutingCore("qwen3"))
    runtime.registry.register(_FunctionRoutingCore("codestral"))
    runtime.declare_model_functions("codestral", ("code_generation",))
    runtime.assign_function("code_generation", "codestral")

    result = runtime.analyze_for_function("code_generation", "write a function")

    assert [item.model_id for item in result.results] == ["codestral"]
    assert runtime.status()["function_assignments"] == {
        "code_generation": ("codestral",)
    }


def test_function_routing_restores_and_fails_closed_for_unassigned_function():
    storage = _FunctionRoutingStorage()
    runtime = PersistentAIRuntime(storage, local_cores=False)
    runtime.registry.register(_FunctionRoutingCore("qwen3"))
    runtime.declare_model_functions("qwen3", ("reasoning",))
    runtime.assign_function("reasoning", "qwen3")
    runtime.save()

    restored = PersistentAIRuntime(storage, local_cores=False)
    restored.registry.register(_FunctionRoutingCore("qwen3"))
    restored.restore()
    assert restored.function_router.models_for("reasoning") == ("qwen3",)

    try:
        restored.analyze_for_function("communications", "send a message")
    except LookupError as exc:
        assert "no enabled model" in str(exc)
    else:
        raise AssertionError("unassigned function was routed to an arbitrary model")
