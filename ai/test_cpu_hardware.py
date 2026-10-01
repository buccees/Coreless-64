from cpu_hardware import CorelessCPUBridge, CorelessCPUHardware
from hardware_runtime import HardwareRequest
from model_part import (
    Capability, ComponentRole, HardwareAssignment, ModelPart, RoleContract,
    TaskContract,
)


class CPUAdapter:
    def execute_cpu(self, operation, payload):
        return {"operation": operation, "payload": payload, "native": True}


def make_cpu():
    role = RoleContract(
        role=ComponentRole.CPU,
        mandatory_capabilities=("scalar_compute",),
    )
    part = ModelPart(
        "cpu-ai-0", "native-cpu-model",
        TaskContract("cpu", (Capability("execute"),)),
        role_contract=role,
    )
    assignment = HardwareAssignment(
        "trained-cpu-model", "cpu-ai-0", role,
        ("scalar_compute",), (), "native-cpu-model",
    )
    return part, assignment


def test_cpu_binding_requires_cpu_role():
    part, assignment = make_cpu()
    cpu = CorelessCPUHardware(part, assignment, CPUAdapter(), ("scalar_compute",))
    response = CorelessCPUBridge(cpu).handle(
        HardwareRequest("communication-0", "cpu-ai-0", "execute", {"pc": 0})
    )
    assert response.result["native"] is True


def test_cpu_binding_rejects_non_cpu_role():
    part, assignment = make_cpu()
    gpu_role = RoleContract(
        role=ComponentRole.GPU,
        mandatory_capabilities=("matrix_compute",),
    )
    gpu_assignment = HardwareAssignment(
        "trained-gpu-model", "cpu-ai-0", gpu_role,
        ("matrix_compute",), (), "native-gpu-model",
    )
    try:
        CorelessCPUHardware(part, gpu_assignment, CPUAdapter(), ("matrix_compute",))
    except ValueError as exc:
        assert "CPU role" in str(exc)
    else:
        raise AssertionError("non-CPU assignment was accepted")
