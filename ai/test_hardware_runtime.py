from hardware_runtime import (
    CorelessHardwareFabric,
    HardwareEndpoint,
    HardwareRequest,
)
from model_part import (
    Capability,
    ComponentRole,
    HardwareAssignment,
    ModelPart,
    RoleContract,
    TaskContract,
)


class EchoAdapter:
    def execute(self, operation, payload):
        return operation, payload


def make_cpu():
    role = RoleContract(
        role=ComponentRole.CPU,
        mandatory_capabilities=("scalar_compute",),
    )
    part = ModelPart(
        "cpu-0",
        "native-cpu-model",
        TaskContract("cpu", (Capability("execute"),)),
        role_contract=role,
    )
    assignment = HardwareAssignment(
        model_id="cpu-model",
        part_id="cpu-0",
        role_contract=role,
        required_capabilities=("scalar_compute",),
        retained_optional_capabilities=(),
        native_architecture="native-cpu-model",
    )
    return part, assignment


def test_hardware_endpoint_delegates_to_native_adapter():
    part, assignment = make_cpu()
    endpoint = HardwareEndpoint(
        part, assignment, EchoAdapter(), ("scalar_compute",)
    )
    response = endpoint.handle(
        HardwareRequest(
            source="communication-0",
            target="cpu-0",
            operation="execute",
            payload={"instruction": "add"},
            required_capabilities=("scalar_compute",),
        )
    )
    assert response.result == ("execute", {"instruction": "add"})
    assert response.source == "cpu-0"


def test_fabric_routes_between_components():
    part, assignment = make_cpu()
    fabric = CorelessHardwareFabric()
    fabric.attach(HardwareEndpoint(part, assignment, EchoAdapter(), ("scalar_compute",)))
    response = fabric.send(
        HardwareRequest("communication-0", "cpu-0", "execute", 7)
    )
    assert response.result == ("execute", 7)
