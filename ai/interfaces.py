"""Stable interface contracts for Coreless-64 and 314DNest.

These are intentionally dependency-free. Concrete runtimes, local model servers,
and external gateways implement these contracts without becoming part of the
Coreless architectural authority path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence


class AuthorityLevel(str, Enum):
    OBSERVE = "observe"
    RECOMMEND = "recommend"
    ASK = "ask"
    POLICY = "policy"
    SAFE = "safe"


@dataclass(frozen=True)
class AIRequest:
    request_id: str
    prompt: str
    context: Mapping[str, Any] = field(default_factory=dict)
    authority: AuthorityLevel = AuthorityLevel.RECOMMEND


@dataclass(frozen=True)
class AIResult:
    request_id: str
    model_id: str
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIProposal:
    proposal_id: str
    source_model: str
    operation: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    rationale: str = ""
    authorization_required: bool = True
    capability: str | None = None


@dataclass(frozen=True)
class GroupResult:
    request_id: str
    participants: Sequence[str]
    proposals: Sequence[AIProposal]
    agreements: Sequence[str] = ()
    disagreements: Sequence[str] = ()
    resolution: str = ""
    confidence: float | None = None
    recommended_action: AIProposal | None = None
    authorization_required: bool = True


class ComputeInterface(Protocol):
    def submit(self, operation: str, payload: Mapping[str, Any]) -> str: ...


class MemoryInterface(Protocol):
    def read(self, address: int, size: int) -> bytes: ...
    def write(self, address: int, data: bytes) -> None: ...


class IOInterface(Protocol):
    def emit(self, device: str, payload: Mapping[str, Any]) -> None: ...


class StorageInterface(Protocol):
    def read(self, key: str) -> bytes: ...
    def write(self, key: str, data: bytes) -> None: ...


class NetworkInterface(Protocol):
    def request(self, endpoint: str, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...


class FabricInterface(Protocol):
    def send(self, destination: str, message: Mapping[str, Any]) -> str: ...


class AICore(Protocol):
    @property
    def model_id(self) -> str: ...
    def infer(self, request: AIRequest) -> AIResult: ...


class CollaborationInterface(Protocol):
    def publish(self, result: AIResult) -> None: ...
    def deliberate(self, request: AIRequest, results: Sequence[AIResult]) -> GroupResult: ...


class PolicyInterface(Protocol):
    def authorize(self, proposal: AIProposal) -> bool: ...
    def execute(self, proposal: AIProposal) -> Mapping[str, Any]: ...
