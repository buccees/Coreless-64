from ai.interfaces import AIRequest, AIResult
from ai.registry import AICoreRegistry
from ai.compute_fabric import ComputeWork
from machine_runtime import CorelessMachine


class EchoCore:
    model_id = "test-model"

    def infer(self, request):
        return AIResult(request.request_id, self.model_id, "ok", {"source": "test"})


def make_machine():
    machine = CorelessMachine(memory_size=4096)
    registry = AICoreRegistry()
    registry.register(EchoCore())
    machine.attach_ai_registry(registry)
    return machine


def test_chipset_is_attached_to_canonical_motherboard_and_ready_signal():
    machine = make_machine()
    assert machine.ai_chipset.machine is machine
    assert machine.motherboard.ai_chipset_status() == {
        "ready": True, "busy": False, "fault": False, "enabled": True
    }
    assert all(machine.motherboard.continuity_report().values())


def test_chipset_dispatch_uses_existing_ai_fabric_and_preserves_provenance():
    machine = make_machine()
    request = AIRequest("request-1", "hello")
    work = ComputeWork("work-1", "ai.infer", request, "test-model")

    result = machine.ai_chipset.dispatch(work)

    assert result.work_id == "work-1"
    assert result.operation == "ai.infer"
    assert result.model_id == "test-model"
    assert result.result.text == "ok"
    assert machine.ai_chipset.snapshot()["last_resource_id"] == "ai:test-model"
    assert machine.ai_chipset.snapshot()["completed_work"] == 1
    assert machine.motherboard.ai_chipset_status()["busy"] is False


def test_chipset_rejects_unsupported_operations_without_dispatch():
    machine = make_machine()
    work = ComputeWork("work-2", "filesystem.delete", AIRequest("request-2", "no"), "test-model")
    import pytest
    with pytest.raises(ValueError, match="unsupported"):
        machine.ai_chipset.dispatch(work)
    assert machine.ai_chipset.snapshot()["completed_work"] == 0


def test_chipset_disable_reset_and_fault_clear_are_control_only():
    machine = make_machine()
    chipset = machine.ai_chipset
    chipset.disable()
    assert machine.motherboard.ai_chipset_status()["enabled"] is False
    assert machine.motherboard.ai_chipset_status()["ready"] is False
    import pytest
    with pytest.raises(RuntimeError, match="disabled"):
        chipset.dispatch(ComputeWork("work-3", "ai.infer", AIRequest("request-3", "x"), "test-model"))
    chipset.enable()
    chipset.fault = "injected"
    chipset._publish()
    assert machine.motherboard.ai_chipset_status()["fault"] is True
    chipset.clear_fault()
    chipset.reset()
    assert machine.motherboard.ai_chipset_status()["fault"] is False
    assert machine.ai_fabric.resources() == ("test-model",)
