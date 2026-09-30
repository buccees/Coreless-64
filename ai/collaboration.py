"""Deterministic 314DNest collaboration coordinator.

This module coordinates AI results without becoming an AI model or a
privileged authority. It only aggregates explicit structured proposals and
produces a deterministic GroupResult. Protected actions remain subject to the
Policy interface.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from .interfaces import AIProposal, AIRequest, AIResult, CollaborationInterface, GroupResult


class DeterministicCollaboration(CollaborationInterface):
    """Collect and reconcile explicit proposals from participating AI cores."""

    def __init__(self) -> None:
        self._published: dict[str, list[AIResult]] = defaultdict(list)

    def publish(self, result: AIResult) -> None:
        self._published[result.request_id].append(result)

    def deliberate(
        self,
        request: AIRequest,
        results: Sequence[AIResult] | None = None,
    ) -> GroupResult:
        candidates = tuple(results) if results is not None else tuple(
            self._published.get(request.request_id, ())
        )
        participants = tuple(result.model_id for result in candidates)

        proposals = tuple(
            proposal
            for result in candidates
            if (proposal := self._proposal_from_result(result)) is not None
        )

        groups: dict[tuple[str, tuple[tuple[str, object], ...]], list[AIProposal]] = defaultdict(list)
        for proposal in proposals:
            arguments = tuple(sorted(proposal.arguments.items(), key=lambda item: item[0]))
            groups[(proposal.operation, arguments)].append(proposal)

        agreements = []
        disagreements = []
        recommended_action = None

        if not proposals:
            disagreements.append("no structured proposals were supplied")
        elif len(groups) == 1:
            only_group = next(iter(groups.values()))
            agreements.append("participating cores supplied the same operation and arguments")
            recommended_action = only_group[0]
        else:
            disagreements.append("participating cores supplied conflicting operations or arguments")

        return GroupResult(
            request_id=request.request_id,
            participants=participants,
            proposals=proposals,
            agreements=tuple(agreements),
            disagreements=tuple(disagreements),
            resolution=(
                "consensus proposal selected deterministically"
                if recommended_action is not None
                else "no consensus; human or policy-directed reconciliation is required"
            ),
            confidence=(
                1.0 if recommended_action is not None and proposals else None
            ),
            recommended_action=recommended_action,
            authorization_required=True,
        )

    @staticmethod
    def _proposal_from_result(result: AIResult) -> AIProposal | None:
        raw = result.metadata.get("proposal")
        if not isinstance(raw, AIProposal):
            return None
        if raw.source_model != result.model_id:
            raise ValueError("proposal source_model must match AIResult.model_id")
        return raw
