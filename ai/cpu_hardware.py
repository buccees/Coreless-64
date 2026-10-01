"""CPU hardware-role binding for AI-derived Coreless CPU parts.

The binding connects a validated CPU ModelPart to the existing Coreless-64
architectural CPU boundary. The native model runtime is supplied separately;
this module never substitutes a generic Transformer for the assigned model.
"""

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from model_part import ComponentRole, HardwareAssignment, ModelPart
from hardware_runtime import HardwareEndpoint, HardwareRequest, HardwareResponse


class CPUModelExecutionAdapter(Protocol):
    """Native execution adapter for the model assigned to the CPU role."""

    def execute_cpu(self, operation: str, payload: Any) -> Any:
        ...


@dataclass
class CorelessCPUHardware:
    """A validated AI-derived CPU endpoint."""

    part: ModelPart
    assignment: HardwareAssignment
    adapter: CPUModelExecutionAdapter
    available_capabilities: Sequence[str]

    def __post_init__(self) -> None:
        if self.assignment.role_contract.role is not ComponentRole.CPU:
            raise ValueError("CPU hardware requires a CPU role assignment")
        self.assignment.validate(self.available_capabilities)
        if self.assignment.part_id != self.part.part_id:
            raise ValueError("CPU assignment and model part IDs do not match")

    def request(self, source: str, operation: str, payload: Any) -> Any:
        return self.adapter.execute_cpu(operation, payload)


class CorelessCPUBridge:
    """Routes Coreless CPU operations through the assigned model adapter."""

    def __init__(self, hardware: CorelessCPUHardware):
        self.hardware = hardware

    def handle(self, request: HardwareRequest) -> HardwareResponse:
        if request.target != self.hardware.part.part_id:
            raise ValueError("request target does not match CPU hardware")
        result = self.hardware.request(
            request.source, request.operation, request.payload
        )
        return HardwareResponse(
            source=self.hardware.part.part_id,
            target=request.source,
            operation=request.operation,
            result=result,
        )
