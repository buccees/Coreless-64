"""Coreless AI hardware execution bridge.

This layer turns a validated ModelPart assignment into a routable hardware
endpoint. It deliberately does not replace a model's native execution engine:
the endpoint delegates execution to an architecture-specific adapter.

The bridge provides the stable Coreless side of the boundary:
role, capabilities, requests, responses, and component-to-component routing.
"""

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Protocol, Sequence, Tuple

from model_part import ComponentRole, HardwareAssignment, ModelPart


@dataclass(frozen=True)
class HardwareRequest:
    source: str
    target: str
    operation: str
    payload: Any
    required_capabilities: Tuple[str, ...] = ()


@dataclass(frozen=True)
class HardwareResponse:
    source: str
    target: str
    operation: str
    result: Any


class NativeExecutionAdapter(Protocol):
    """Adapter implemented by each model architecture's native runtime."""

    def execute(self, operation: str, payload: Any) -> Any:
        ...


class HardwareEndpoint:
    """Execution endpoint for one validated model-derived hardware part."""

    def __init__(
        self,
        part: ModelPart,
        assignment: HardwareAssignment,
        adapter: NativeExecutionAdapter,
        available_capabilities: Sequence[str],
    ) -> None:
        assignment.validate(available_capabilities)
        if assignment.part_id != part.part_id:
            raise ValueError("assignment and model part IDs do not match")
        if assignment.role_contract.role is not part.role_contract.role:
            raise ValueError("assignment and model-part roles do not match")
        self.part = part
        self.assignment = assignment
        self.adapter = adapter

    @property
    def role(self) -> ComponentRole:
        return self.assignment.role_contract.role

    def handle(self, request: HardwareRequest) -> HardwareResponse:
        if request.target != self.part.part_id:
            raise ValueError("request target does not match hardware endpoint")
        required = set(request.required_capabilities)
        available = set(self.part.required_capabilities())
        missing = required - available
        if missing:
            raise PermissionError(
                f"{self.part.part_id} does not expose requested capabilities: "
                f"{sorted(missing)}"
            )
        result = self.adapter.execute(request.operation, request.payload)
        return HardwareResponse(
            source=self.part.part_id,
            target=request.source,
            operation=request.operation,
            result=result,
        )


class CorelessHardwareFabric:
    """Routes requests between assigned AI-derived hardware components."""

    def __init__(self) -> None:
        self._endpoints: Dict[str, HardwareEndpoint] = {}

    def attach(self, endpoint: HardwareEndpoint) -> None:
        if endpoint.part.part_id in self._endpoints:
            raise ValueError(f"hardware endpoint already attached: {endpoint.part.part_id}")
        self._endpoints[endpoint.part.part_id] = endpoint

    def send(self, request: HardwareRequest) -> HardwareResponse:
        try:
            endpoint = self._endpoints[request.target]
        except KeyError as exc:
            raise KeyError(f"unknown hardware endpoint: {request.target}") from exc
        return endpoint.handle(request)

    def roles(self) -> Tuple[ComponentRole, ...]:
        return tuple(endpoint.role for endpoint in self._endpoints.values())
