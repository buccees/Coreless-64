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

    assert "cpu-0" in snapshot.cpu
    assert snapshot.memory["ram_bytes"] == 4096
    assert snapshot.storage["objects"] >= 0
