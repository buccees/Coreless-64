import pytest

from ai.execution_paths import ExecutionPath, ExecutionPathRegistry
from ai.function_router import FunctionalModelRouter


class _Descriptor:
    def __init__(self, model_id):
        self.ai_model_id = model_id


class _Component:
    def __init__(self, model_id, healthy=True, running=True):
        self.descriptor = _Descriptor(model_id)
        self.healthy = healthy
        self._running = running

    def ai_status(self):
        return {"bound": True, "running": self._running}


class _Result:
    def __init__(self, model_id):
        self.model_id = model_id


class _ComputeResult:
    def __init__(self, model_id):
        self.model_id = model_id
        self.result = _Result(model_id)


class _Runtime:
    def __init__(self, router):
        self.function_router = router
        self.calls = []

    def compute(self, machine, text, **kwargs):
        self.calls.append((machine, text, kwargs))
        return (_ComputeResult(kwargs["model_id"]),)


class _Core:
    def __init__(self, model_id):
        self.model_id = model_id


class _Storage:
    def __init__(self):
        self.values = {}

    def put(self, key, value):
        self.values[key] = value

    def get(self, key):
        if key not in self.values:
            raise KeyError(key)
        return self.values[key]


def _router(*model_ids):
    from ai.registry import AICoreRegistry

    registry = AICoreRegistry()
    for model_id in model_ids:
        registry.register(_Core(model_id))
    router = FunctionalModelRouter(registry)
    for model_id in model_ids:
        router.declare_capabilities(model_id, ("cpu_intelligence",))
    return router


def test_execution_path_requires_exact_component_and_single_model_owner():
    router = _router("qwen3", "deepseek")
    router.assign("cpu_intelligence", "qwen3")
    paths = ExecutionPathRegistry()
    path = ExecutionPath("cpu.primary", "cpu-0", "cpu_intelligence", "qwen3")
    paths.register(path)

    assert paths.validate_binding(
        "cpu.primary",
        components={"cpu-0": _Component("qwen3")},
        function_router=router,
    ) == path

    router.assign("cpu_intelligence", "deepseek")
    with pytest.raises(ValueError, match="sole model owner"):
        paths.validate_binding(
            "cpu.primary",
            components={"cpu-0": _Component("qwen3")},
            function_router=router,
        )


def test_execution_path_rejects_missing_or_faulted_component_and_wrong_resident_model():
    router = _router("qwen3")
    router.assign("cpu_intelligence", "qwen3")
    paths = ExecutionPathRegistry()
    paths.register(ExecutionPath("cpu.primary", "cpu-0", "cpu_intelligence", "qwen3"))

    with pytest.raises(LookupError, match="unavailable"):
        paths.validate_binding("cpu.primary", components={}, function_router=router)
    with pytest.raises(RuntimeError, match="fault-isolated"):
        paths.validate_binding(
            "cpu.primary",
            components={"cpu-0": _Component("qwen3", healthy=False)},
            function_router=router,
        )
    with pytest.raises(ValueError, match="does not match component"):
        paths.validate_binding(
            "cpu.primary",
            components={"cpu-0": _Component("deepseek")},
            function_router=router,
        )


def test_execution_path_registry_rejects_overlapping_component_function_ownership():
    paths = ExecutionPathRegistry()
    paths.register(ExecutionPath("cpu.primary", "cpu-0", "cpu_intelligence", "qwen3"))
    with pytest.raises(ValueError, match="already has an owner"):
        paths.register(
            ExecutionPath("cpu.backup", "cpu-0", "cpu_intelligence", "deepseek")
        )


def test_execution_path_registry_persists_and_restores():
    storage = _Storage()
    paths = ExecutionPathRegistry()
    paths.register(
        ExecutionPath("chipset.interpret", "chipset-0", "chipset_interpretation", "gpt-oss")
    )
    paths.save(storage)

    restored = ExecutionPathRegistry()
    restored.load(storage)
    assert restored.all() == paths.all()
    assert restored.get("chipset.interpret").operation == "ai.infer"


def test_execution_path_registry_rejects_duplicate_owner_on_restore():
    paths = ExecutionPathRegistry()
    with pytest.raises(ValueError, match="already has an owner"):
        paths.restore_state({
            "version": 1,
            "paths": [
                {"path_id": "a", "component_id": "cpu-0", "function_id": "reason", "model_id": "qwen3"},
                {"path_id": "b", "component_id": "cpu-0", "function_id": "reason", "model_id": "deepseek"},
            ],
        })



def test_execute_dispatches_only_registered_model_and_checks_provenance():
    router = _router("qwen3", "deepseek")
    router.assign("cpu_intelligence", "qwen3")
    paths = ExecutionPathRegistry()
    paths.register(ExecutionPath("cpu.primary", "cpu-0", "cpu_intelligence", "qwen3"))
    runtime = _Runtime(router)
    machine = object()

    result = paths.execute(
        "cpu.primary",
        components={"cpu-0": _Component("qwen3")},
        runtime=runtime,
        machine=machine,
        text="inspect CPU workload",
    )

    assert result.model_id == "qwen3"
    assert len(runtime.calls) == 1
    assert runtime.calls[0][2]["model_id"] == "qwen3"
    assert runtime.calls[0][2]["context"]["execution_path_id"] == "cpu.primary"


def test_execute_fails_closed_when_component_ai_is_not_running():
    router = _router("qwen3")
    router.assign("cpu_intelligence", "qwen3")
    paths = ExecutionPathRegistry()
    paths.register(ExecutionPath("cpu.primary", "cpu-0", "cpu_intelligence", "qwen3"))

    with pytest.raises(RuntimeError, match="AI is not running"):
        paths.execute(
            "cpu.primary",
            components={"cpu-0": _Component("qwen3", running=False)},
            runtime=_Runtime(router),
            machine=object(),
            text="must not dispatch",
        )



def test_persistent_runtime_includes_execution_paths_in_state():
    from ai.machine_runtime import PersistentAIRuntime

    runtime = PersistentAIRuntime(_Storage(), local_cores=False)
    path = ExecutionPath("cpu.primary", "cpu-0", "cpu_intelligence", "qwen3")
    runtime.execution_paths.register(path)

    state = runtime.state()
    restored = PersistentAIRuntime(_Storage(), local_cores=False)
    restored.restore_state(state)

    assert restored.execution_paths.get("cpu.primary") == path
    assert restored.status()["execution_paths"] == [path.to_dict()]
