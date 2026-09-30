"""Deterministic policy boundary for AI-proposed Coreless actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .interfaces import AIProposal, AuthorityLevel, PolicyInterface


@dataclass(frozen=True)
class PolicyDecision:
    proposal_id: str
    allowed: bool
    reason: str


class DeterministicPolicy(PolicyInterface):
    """Allow only explicitly registered operations under explicit policy."""

    def __init__(self) -> None:
        self._operations: dict[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]] = {}
        self._levels: dict[str, AuthorityLevel] = {}
        self._approvals: set[str] = set()
        self._capabilities: dict[str, str] = {}

    def register(
        self,
        operation: str,
        handler: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        *,
        authority: AuthorityLevel = AuthorityLevel.POLICY,
    ) -> None:
        if not operation or operation in self._operations:
            raise ValueError("operation must be non-empty and unique")
        if authority in (AuthorityLevel.OBSERVE, AuthorityLevel.RECOMMEND):
            raise ValueError("execution requires ASK, POLICY, or SAFE authority")
        self._operations[operation] = handler
        self._levels[operation] = authority

    def grant_capability(self, capability: str, operation: str) -> None:
        if not capability or not operation or operation not in self._operations:
            raise ValueError("capability must target a registered operation")
        self._capabilities[capability] = operation

    def revoke_capability(self, capability: str) -> None:
        self._capabilities.pop(capability, None)

    def approve(self, proposal_id: str) -> None:
        self._approvals.add(proposal_id)

    def revoke_approval(self, proposal_id: str) -> None:
        self._approvals.discard(proposal_id)

    def authorize(self, proposal: AIProposal) -> bool:
        if proposal.operation not in self._operations:
            return False
        if self._capabilities.get(proposal.capability) != proposal.operation:
            return False
        level = self._levels[proposal.operation]
        if level is AuthorityLevel.SAFE:
            return True
        if level is AuthorityLevel.POLICY:
            return True
        if level is AuthorityLevel.ASK:
            return proposal.proposal_id in self._approvals
        return False

    def decision(self, proposal: AIProposal) -> PolicyDecision:
        allowed = self.authorize(proposal)
        if allowed:
            return PolicyDecision(proposal.proposal_id, True, "explicit policy permits execution")
        if proposal.operation not in self._operations:
            reason = "operation is not registered"
        elif self._capabilities.get(proposal.capability) != proposal.operation:
            reason = "valid capability for the operation is required"
        elif self._levels[proposal.operation] is AuthorityLevel.ASK:
            reason = "explicit approval is required"
        else:
            reason = "operation authority does not permit execution"
        return PolicyDecision(proposal.proposal_id, False, reason)

    def execute(self, proposal: AIProposal) -> Mapping[str, Any]:
        decision = self.decision(proposal)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        return dict(self._operations[proposal.operation](proposal.arguments))
