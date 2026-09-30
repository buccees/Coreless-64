"""Deterministic policy boundary for AI-proposed Coreless actions.

AI models can propose operations, but only this layer can authorize execution.
Natural-language output is never treated as authorization.
"""

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

    def approve(self, proposal_id: str) -> None:
        self._approvals.add(proposal_id)

    def revoke_approval(self, proposal_id: str) -> None:
        self._approvals.discard(proposal_id)

    def authorize(self, proposal: AIProposal) -> bool:
        if proposal.operation not in self._operations:
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
        elif self._levels[proposal.operation] is AuthorityLevel.ASK:
            reason = "explicit approval is required"
        else:
            reason = "operation authority does not permit execution"
        return PolicyDecision(proposal.proposal_id, False, reason)

    def execute(self, proposal: AIProposal) -> Mapping[str, Any]:
        if not self.authorize(proposal):
            raise PermissionError(self.decision(proposal).reason)
        return dict(self._operations[proposal.operation](proposal.arguments))
