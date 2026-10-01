"""Coreless model-part ABI and static-adaptive specialization contracts.

A ModelPart is the deployable form of a trained model after it has been
specialized for a task. The VM hosts the part; it does not define the
model's internal architecture.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Sequence, Tuple


class PartState(str, Enum):
    CANDIDATE = "candidate"
    VALIDATING = "validating"
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass(frozen=True)
class Capability:
    name: str
    version: int = 1
    inputs: Tuple[str, ...] = ()
    outputs: Tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskContract:
    task_id: str
    capabilities: Tuple[Capability, ...]
    constraints: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ComponentRole(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    COMMUNICATION = "communication"
    OTHER = "other"


@dataclass(frozen=True)
class RoleContract:
    """Complete hardware role contract for a model-derived component."""

    role: ComponentRole
    mandatory_capabilities: Tuple[str, ...] = ()
    retained_optional_capabilities: Tuple[str, ...] = ()
    removable_capabilities: Tuple[str, ...] = ()
    user_communication: bool = False

    def __post_init__(self) -> None:
        mandatory = set(self.mandatory_capabilities)
        retained = set(self.retained_optional_capabilities)
        removable = set(self.removable_capabilities)
        if mandatory & removable:
            raise ValueError("a mandatory capability cannot be removable")
        if retained & removable:
            raise ValueError("a retained optional capability cannot be removable")
        if self.role is ComponentRole.COMMUNICATION and not self.user_communication:
            raise ValueError("communication components must retain user communication")


@dataclass(frozen=True)
class AdaptationRecord:
    source_part_id: str
    candidate_part_id: str
    task_id: str
    reason: str
    validation_passed: bool


@dataclass
class ModelPart:
    """A model-derived computational component hosted by a Coreless VM."""

    part_id: str
    architecture: str
    task_contract: TaskContract
    role_contract: RoleContract = field(default_factory=lambda: RoleContract(role=ComponentRole.OTHER))
    state: PartState = PartState.CANDIDATE
    metadata: Dict[str, Any] = field(default_factory=dict)
    retained_parameters: Tuple[str, ...] = ()
    removed_parameters: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Enforce the role contract at component creation time."""
        retained = set(self.retained_parameters)
        removed = set(self.removed_parameters)
        mandatory = set(self.role_contract.mandatory_capabilities)
        protected = mandatory | set(self.role_contract.retained_optional_capabilities)
        if removed & protected:
            raise ValueError("role-required capability cannot be removed")

    def can_remove_capability(self, capability: str) -> bool:
        return (
            capability in self.role_contract.removable_capabilities
            and capability not in self.role_contract.mandatory_capabilities
            and capability not in self.role_contract.retained_optional_capabilities
        )

    def transition(self, state: PartState) -> None:
        allowed = {
            PartState.CANDIDATE: {PartState.VALIDATING, PartState.RETIRED},
            PartState.VALIDATING: {PartState.ACTIVE, PartState.RETIRED},
            PartState.ACTIVE: {PartState.RETIRED, PartState.VALIDATING},
            PartState.RETIRED: set(),
        }
        if state not in allowed[self.state]:
            raise ValueError(f"invalid model-part transition: {self.state} -> {state}")
        self.state = state

    def satisfies(self, task_id: str, capability: str) -> bool:
        return (
            self.task_contract.task_id == task_id
            and any(c.name == capability for c in self.task_contract.capabilities)
        )


class StaticAdaptiveSpecializer:
    """Plans replacement components without mutating the active component.

    Adaptation is candidate-based: a new part must be validated before it can
    replace the active part. The specializer intentionally does not prescribe
    how a model is trained or which architecture is used.
    """

    def propose(
        self,
        active: ModelPart,
        task: TaskContract,
        *,
        reason: str,
        candidate_id: str,
    ) -> ModelPart:
        return ModelPart(
            part_id=candidate_id,
            architecture=active.architecture,
            task_contract=task,
            metadata={
                "specialization_source": active.part_id,
                "adaptation_reason": reason,
                "parent_architecture": active.architecture,
            },
        )

    def validate(
        self,
        candidate: ModelPart,
        checks: Sequence[bool],
    ) -> bool:
        candidate.transition(PartState.VALIDATING)
        passed = bool(checks) and all(checks)
        if passed:
            candidate.transition(PartState.ACTIVE)
        else:
            candidate.transition(PartState.RETIRED)
        return passed

    def commit_replacement(
        self,
        active: ModelPart,
        candidate: ModelPart,
    ) -> AdaptationRecord:
        if candidate.state is not PartState.ACTIVE:
            raise ValueError("only a validated active candidate can replace a part")
        if active.state is not PartState.ACTIVE:
            raise ValueError("source part must be active")
        active.transition(PartState.RETIRED)
        return AdaptationRecord(
            source_part_id=active.part_id,
            candidate_part_id=candidate.part_id,
            task_id=candidate.task_contract.task_id,
            reason=str(candidate.metadata.get("adaptation_reason", "")),
            validation_passed=True,
        )
