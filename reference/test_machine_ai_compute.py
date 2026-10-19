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
    from types import SimpleNamespace

    from ai.execution_paths import ExecutionPath, ExecutionPathRegistry
    from ai.machine_runtime import PersistentAIRuntime
    from components import ComponentDescriptor, CorelessComponent, CorelessHub

    machine = CorelessMachine(memory_size=4096)
    runtime = PersistentAIRuntime(machine.storage, local_cores=False)
    runtime.registry.register(FakeCore())
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
        ai_runtime=SimpleNamespace(running=True),
    )
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
