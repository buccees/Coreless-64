from ai.compute_fabric import ComputeWork
from ai.interfaces import AIRequest, AIResult
from ai.registry import AICoreRegistry
from machine_runtime import CorelessMachine


class FakeCore:
    model_id = "qwen3"

    def infer(self, request):
        return AIResult(
            model_id=self.model_id,
            request_id=request.request_id,
            text="ai-computed",
            metadata={"role": "compute"},
        )


def test_machine_exposes_ai_as_native_compute_resource():
    machine = CorelessMachine(memory_size=4096)
    registry = AICoreRegistry()
    registry.register(FakeCore())
    assert machine.attach_ai_registry(registry) == ("qwen3",)

    work = ComputeWork(
        "work-1",
        "accelerate.scheduler",
        AIRequest("request-1", "optimize this workload", {"machine": "coreless"}),
    )
    result = machine.ai_compute(work, "qwen3")

    assert result.work_id == "work-1"
    assert result.operation == "accelerate.scheduler"
    assert result.model_id == "qwen3"
    assert result.result.text == "ai-computed"


def test_existing_machine_components_remain_available_with_ai():
    machine = CorelessMachine(memory_size=4096)
    assert machine.cpu is machine.cpus[0]
    assert machine.storage is not None
    assert machine.network is not None
    assert machine.graphics is not None
    assert machine.devices.discover()
    assert machine.ai_fabric.resources() == ()


def test_machine_scheduler_publishes_telemetry():
    from machine_runtime import CorelessMachine

    machine = CorelessMachine(memory_size=4096)
    snapshot = machine.publish_telemetry()

    assert "cpu" in snapshot.cpu
    assert snapshot.memory["ram_bytes"] == 4096
    assert snapshot.storage["objects"] >= 0

def test_machine_ai_resources_advertise_explicit_capabilities():
    machine = CorelessMachine(memory_size=4096)
    registry = AICoreRegistry()
    registry.register(FakeCore())
    machine.attach_ai_registry(registry)
    resource = next(r for r in machine.scheduler._resources.values() if r.resource_id == "ai:qwen3")
    assert "tensor.matmul" in resource.capabilities
    assert "transformer.attention" in resource.capabilities
    assert "ai.infer" in resource.capabilities
    assert "unknown.operation" not in resource.capabilities

def test_hub_owned_ai_path_runs_through_real_machine_scheduler_and_fabric():
    from ai.execution_paths import ExecutionPath, ExecutionPathRegistry
    from ai.machine_runtime import PersistentAIRuntime
    from components import ComponentDescriptor, CorelessComponent, CorelessHub

    machine = CorelessMachine(memory_size=4096)
    runtime = PersistentAIRuntime(machine.storage, local_cores=False)
    core = FakeCore()
    runtime.registry.register(core)
    assert machine.attach_ai_registry(runtime.registry) == ("qwen3",)
    runtime.function_router.declare_capabilities("qwen3", ("cpu_intelligence",))
    runtime.function_router.assign("cpu_intelligence", "qwen3")

    component = CorelessComponent(
        ComponentDescriptor(
            component_id="cpu-0",
            role="cpu",
            capabilities=frozenset(),
            ai_model_id="qwen3",
        ),
        ai_runtime=core,
    )
    component.start_ai()
    hub = CorelessHub("integration-test-hub")
    hub.connect(component)

    paths = ExecutionPathRegistry()
    paths.register(
        ExecutionPath(
            path_id="cpu.primary",
            component_id="cpu-0",
            function_id="cpu_intelligence",
            model_id="qwen3",
        )
    )

    result = hub.dispatch_ai_path(
        "cpu.primary",
        execution_paths=paths,
        runtime=runtime,
        machine=machine,
        text="execute the CPU intelligence path",
    )

    assert result.work_id.startswith("default:work:")
    assert result.operation == "ai.infer"
    assert result.model_id == "qwen3"
    assert result.result.model_id == "qwen3"
    assert result.result.text == "ai-computed"
    assert runtime.session.events()[-1].kind == "result"
    assert runtime.session.events()[-1].payload["text"] == "ai-computed"

def _owned_ai_path_system():
    from ai.execution_paths import ExecutionPath, ExecutionPathRegistry
    from ai.machine_runtime import PersistentAIRuntime
    from components import ComponentDescriptor, CorelessComponent, CorelessHub

    machine = CorelessMachine(memory_size=4096)
    runtime = PersistentAIRuntime(machine.storage, local_cores=False)
    core = FakeCore()
    runtime.registry.register(core)
    machine.attach_ai_registry(runtime.registry)
    runtime.function_router.declare_capabilities("qwen3", ("cpu_intelligence",))
    runtime.function_router.assign("cpu_intelligence", "qwen3")
    component = CorelessComponent(
        ComponentDescriptor(
            component_id="cpu-0",
            role="cpu",
            capabilities=frozenset(),
            ai_model_id="qwen3",
        ),
        ai_runtime=core,
    )
    component.start_ai()
    hub = CorelessHub("fault-recovery-test-hub")
    hub.connect(component)
    paths = ExecutionPathRegistry()
    paths.register(ExecutionPath("cpu.primary", "cpu-0", "cpu_intelligence", "qwen3"))
    return machine, runtime, component, hub, paths


def test_owned_ai_path_fails_closed_after_component_disconnect_and_recovers_on_reconnect():
    import pytest

    machine, runtime, component, hub, paths = _owned_ai_path_system()
    first = hub.dispatch_ai_path(
        "cpu.primary", execution_paths=paths, runtime=runtime, machine=machine,
        text="before disconnect",
    )
    assert first.result.text == "ai-computed"

    hub.disconnect("cpu-0")
    with pytest.raises(LookupError, match="unavailable"):
        hub.dispatch_ai_path(
            "cpu.primary", execution_paths=paths, runtime=runtime, machine=machine,
            text="must not dispatch while disconnected",
        )

    hub.connect(component)
    recovered = hub.dispatch_ai_path(
        "cpu.primary", execution_paths=paths, runtime=runtime, machine=machine,
        text="after reconnect",
    )
    assert recovered.result.text == "ai-computed"


def test_owned_ai_path_requires_ai_restart_after_fault_isolation_and_rejoin():
    import pytest

    machine, runtime, component, hub, paths = _owned_ai_path_system()
    hub.isolate("cpu-0", "simulated AI component fault")
    assert component.ai_status()["running"] is False
    with pytest.raises(LookupError, match="unavailable"):
        hub.dispatch_ai_path(
            "cpu.primary", execution_paths=paths, runtime=runtime, machine=machine,
            text="must not dispatch while isolated",
        )

    hub.rejoin(component)
    with pytest.raises(RuntimeError, match="AI is not running"):
        hub.dispatch_ai_path(
            "cpu.primary", execution_paths=paths, runtime=runtime, machine=machine,
            text="must not dispatch before AI restart",
        )

    component.start_services()
    result = hub.dispatch_ai_path(
        "cpu.primary", execution_paths=paths, runtime=runtime, machine=machine,
        text="after explicit service restart",
    )
    assert result.result.text == "ai-computed"


def test_owned_ai_path_does_not_record_success_when_chipset_dispatch_fails(monkeypatch):
    import pytest

    machine, runtime, component, hub, paths = _owned_ai_path_system()

    def fail_closed(work, *, model_id):
        raise RuntimeError("simulated chipset unavailable")

    monkeypatch.setattr(machine.ai_chipset, "dispatch", fail_closed)
    with pytest.raises(RuntimeError, match="chipset unavailable"):
        hub.dispatch_ai_path(
            "cpu.primary", execution_paths=paths, runtime=runtime, machine=machine,
            text="chipset failure injection",
        )

    result_events = [event for event in runtime.session.events() if event.kind == "result"]
    assert result_events == []


def test_all_resident_ai_components_bind_once_and_route_only_their_assigned_model():
    from ai.execution_paths import ExecutionPath, ExecutionPathRegistry
    from ai.machine_runtime import PersistentAIRuntime
    from components import ComponentDescriptor, CorelessComponent, CorelessHub

    class RecordingCore:
        def __init__(self, model_id):
            self.model_id = model_id
            self.calls = 0

        def infer(self, request):
            self.calls += 1
            return AIResult(
                model_id=self.model_id,
                request_id=request.request_id,
                text=f"executed:{self.model_id}",
                metadata={"test_double": True},
            )

    machine = CorelessMachine(memory_size=4096)
    runtime = PersistentAIRuntime(machine.storage, local_cores=False)
    model_ids = ("qwen3", "gpt-oss", "deepseek", "gemma", "codestral")
    cores = {model_id: RecordingCore(model_id) for model_id in model_ids}
    for core in cores.values():
        runtime.registry.register(core)
    assert machine.attach_ai_registry(runtime.registry) == tuple(sorted(model_ids))

    role_bindings = {
        "cpu-0": ("cpu", "qwen3", ("cpu_intelligence",)),
        "chipset-0": ("chipset", "gpt-oss", ("chipset_request_interpretation",)),
        "reasoning-0": ("reasoning", "deepseek", ("deep_reasoning", "technical_planning")),
        "input-0": ("communication", "gemma", ("input_context", "communication_response")),
        "code-0": ("other", "codestral", ("code_generation", "code_review")),
    }
    hub = CorelessHub("all-resident-ai-components")
    components = {}
    for component_id, (role, model_id, functions) in role_bindings.items():
        component = CorelessComponent(ComponentDescriptor(
            component_id=component_id,
            role=role,
            capabilities=frozenset(functions),
            ai_model_id=model_id,
        ))
        hub.connect(component)
        components[component_id] = component
        runtime.function_router.declare_capabilities(model_id, functions)
        for function in functions:
            runtime.function_router.assign(function, model_id)

    assert hub.bind_resident_ai_components(runtime.registry) == {
        "cpu-0": "qwen3",
        "chipset-0": "gpt-oss",
        "reasoning-0": "deepseek",
        "input-0": "gemma",
        "code-0": "codestral",
    }
    for component_id, (_role, model_id, _functions) in role_bindings.items():
        component = components[component_id]
        assert component.ai_runtime is cores[model_id]
        assert component.bind_registered_ai(runtime.registry) is cores[model_id]
        component.start_services()

    # Each function gets one explicit path. Multiple functions reuse one resident
    # DeepSeek/Gemma object rather than duplicating a model registration.
    paths = ExecutionPathRegistry()
    path_specs = (
        ("cpu.primary", "cpu-0", "cpu_intelligence", "qwen3"),
        ("chipset.ai", "chipset-0", "chipset_request_interpretation", "gpt-oss"),
        ("reasoning.deep", "reasoning-0", "deep_reasoning", "deepseek"),
        ("reasoning.plan", "reasoning-0", "technical_planning", "deepseek"),
        ("input.context", "input-0", "input_context", "gemma"),
        ("input.response", "input-0", "communication_response", "gemma"),
        ("code.generate", "code-0", "code_generation", "codestral"),
        ("code.review", "code-0", "code_review", "codestral"),
    )
    for path_id, component_id, function_id, model_id in path_specs:
        paths.register(ExecutionPath(path_id, component_id, function_id, model_id))

    for path_id, _component_id, _function_id, model_id in path_specs:
        result = hub.dispatch_ai_path(
            path_id,
            execution_paths=paths,
            runtime=runtime,
            machine=machine,
            text=f"test assigned route {path_id}",
        )
        assert result.model_id == model_id
        assert result.result.model_id == model_id
        assert result.result.text == f"executed:{model_id}"

    assert len(runtime.registry.descriptors()) == 5
    assert machine.ai_fabric.resources() == tuple(sorted(model_ids))
    assert {model_id: core.calls for model_id, core in cores.items()} == {
        "qwen3": 1,
        "gpt-oss": 1,
        "deepseek": 2,
        "gemma": 2,
        "codestral": 2,
    }


def test_component_resident_ai_binding_rejects_a_different_existing_runtime():
    import pytest
    from components import ComponentDescriptor, CorelessComponent
    from ai.registry import AICoreRegistry

    registry = AICoreRegistry()
    registered = FakeCore()
    registry.register(registered)

    class DifferentCore:
        model_id = "qwen3"

        def infer(self, request):
            return AIResult(
                model_id=self.model_id, request_id=request.request_id, text="wrong core"
            )

    component = CorelessComponent(
        ComponentDescriptor(
            component_id="cpu-mismatch",
            role="cpu",
            capabilities=frozenset(),
            ai_model_id="qwen3",
        ),
        ai_runtime=DifferentCore(),
    )
    with pytest.raises(RuntimeError, match="already bound to a different AI runtime"):
        component.bind_registered_ai(registry)


def test_hub_resident_binding_prevalidates_before_mutating_any_component():
    import pytest
    from components import ComponentDescriptor, CorelessComponent, CorelessHub
    from ai.registry import AICoreRegistry

    registry = AICoreRegistry()
    qwen = FakeCore()
    class DeepSeekCore:
        model_id = "deepseek"
        def infer(self, request):
            return AIResult(
                model_id=self.model_id, request_id=request.request_id, text="deepseek"
            )
    registry.register(qwen)
    registered_deepseek = DeepSeekCore()
    registry.register(registered_deepseek)

    cpu = CorelessComponent(ComponentDescriptor(
        component_id="cpu-atomic", role="cpu", capabilities=frozenset(),
        ai_model_id="qwen3",
    ))
    wrong_deepseek = DeepSeekCore()
    reasoning = CorelessComponent(ComponentDescriptor(
        component_id="reasoning-atomic", role="reasoning", capabilities=frozenset(),
        ai_model_id="deepseek",
    ), ai_runtime=wrong_deepseek)
    hub = CorelessHub("resident-binding-atomicity")
    hub.connect(cpu)
    hub.connect(reasoning)

    with pytest.raises(RuntimeError, match="different AI runtime"):
        hub.bind_resident_ai_components(registry)
    assert cpu.ai_runtime is None
    assert reasoning.ai_runtime is wrong_deepseek
