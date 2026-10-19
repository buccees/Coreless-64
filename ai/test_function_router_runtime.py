from ai.interfaces import AIResult
from ai.machine_runtime import PersistentAIRuntime


class StubCore:
    def __init__(self, model_id):
        self.model_id = model_id

    def infer(self, request):
        return AIResult(request.request_id, self.model_id, f"result from {self.model_id}")


class MemoryStorage:
    def __init__(self):
        self.values = {}

    def put(self, key, value):
        self.values[key] = value

    def get(self, key):
        if key not in self.values:
            raise KeyError(key)
        return self.values[key]


def test_function_assignment_routes_live_analysis_and_persists():
    storage = MemoryStorage()
    runtime = PersistentAIRuntime(storage, local_cores=False)
    runtime.registry.register(StubCore("qwen3"))
    runtime.registry.register(StubCore("codestral"))

    runtime.assign_function("code_generation", "codestral")
    result = runtime.analyze_for_function("code_generation", "write a function")

    assert [item.model_id for item in result.results] == ["codestral"]
    assert runtime.status()["function_assignments"] == {
        "code_generation": ("codestral",)
    }

    restored = PersistentAIRuntime(storage, local_cores=False)
    restored.registry.register(StubCore("qwen3"))
    restored.registry.register(StubCore("codestral"))
    restored.restore()
    assert restored.function_router.models_for("code_generation") == ("codestral",)


def test_function_analysis_fails_closed_when_no_model_is_assigned():
    runtime = PersistentAIRuntime(MemoryStorage(), local_cores=False)
    runtime.registry.register(StubCore("qwen3"))
    try:
        runtime.analyze_for_function("unassigned_function", "do work")
    except LookupError as exc:
        assert "no enabled model" in str(exc)
    else:
        raise AssertionError("unassigned function was routed to an arbitrary model")
