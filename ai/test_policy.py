from ai.interfaces import AIProposal, AuthorityLevel
from ai.policy import DeterministicPolicy


def proposal(pid="p1", operation="schedule"):
    return AIProposal(
        proposal_id=pid,
        source_model="qwen3",
        operation=operation,
        arguments={"cpu": 1},
    )


def test_unregistered_operation_is_rejected():
    policy = DeterministicPolicy()
    assert policy.authorize(proposal()) is False


def test_policy_authority_allows_only_registered_operations():
    policy = DeterministicPolicy()
    policy.register("schedule", lambda args: {"scheduled": args["cpu"]})
    policy.grant_capability("cap-schedule", "schedule")
    p = proposal()
    p = AIProposal(p.proposal_id, p.source_model, p.operation, p.arguments, p.rationale, p.authorization_required, "cap-schedule")
    assert policy.authorize(p) is True
    assert policy.execute(p) == {"scheduled": 1}


def test_ask_requires_explicit_approval():
    policy = DeterministicPolicy()
    p = proposal()
    policy.register("schedule", lambda args: {"ok": True}, authority=AuthorityLevel.ASK)
    policy.grant_capability("cap-schedule", "schedule")
    p = AIProposal(p.proposal_id, p.source_model, p.operation, p.arguments, p.rationale, p.authorization_required, "cap-schedule")
    assert policy.authorize(p) is False
    policy.approve(p)
    assert policy.authorize(p) is True
    policy.revoke_approval(p)
    assert policy.authorize(p) is False


def test_recommendation_cannot_execute():
    policy = DeterministicPolicy()
    try:
        policy.register("schedule", lambda args: {}, authority=AuthorityLevel.RECOMMEND)
    except ValueError:
        pass
    else:
        raise AssertionError("recommendation authority must not register executable actions")


def test_safe_operation_is_deterministically_executable():
    policy = DeterministicPolicy()
    policy.register("safe_stop", lambda args: {"state": "safe"}, authority=AuthorityLevel.SAFE)
    policy.grant_capability("cap-safe", "safe_stop")
    p = proposal(operation="safe_stop")
    p = AIProposal(p.proposal_id, p.source_model, p.operation, p.arguments, p.rationale, p.authorization_required, "cap-safe")
    assert policy.execute(p) == {"state": "safe"}


def test_capability_cannot_be_silently_reassigned_to_another_operation():
    import pytest

    policy = DeterministicPolicy()
    policy.register("schedule", lambda args: {"scheduled": True})
    policy.register("vm.stop", lambda args: {"stopped": True})
    policy.grant_capability("shared-token", "schedule")

    with pytest.raises(ValueError, match="already bound"):
        policy.grant_capability("shared-token", "vm.stop")

    assert policy.authorize(AIProposal(
        "p-schedule", "qwen3", "schedule", {}, capability="shared-token"
    ))
    assert not policy.authorize(AIProposal(
        "p-stop", "qwen3", "vm.stop", {}, capability="shared-token"
    ))



def test_ask_approval_cannot_be_reused_for_changed_arguments_or_operation():
    policy = DeterministicPolicy()
    policy.register("schedule", lambda args: {"scheduled": True}, authority=AuthorityLevel.ASK)
    policy.register("vm.stop", lambda args: {"stopped": True}, authority=AuthorityLevel.ASK)
    policy.grant_capability("cap-schedule", "schedule")
    policy.grant_capability("cap-stop", "vm.stop")

    approved = AIProposal(
        "reused-id", "qwen3", "schedule", {"cpu": 1},
        capability="cap-schedule",
    )
    changed_arguments = AIProposal(
        "reused-id", "qwen3", "schedule", {"cpu": 2},
        capability="cap-schedule",
    )
    changed_operation = AIProposal(
        "reused-id", "qwen3", "vm.stop", {},
        capability="cap-stop",
    )

    policy.approve(approved)
    assert policy.authorize(approved)
    assert not policy.authorize(changed_arguments)
    assert not policy.authorize(changed_operation)

    policy.revoke_approval(approved)
    assert not policy.authorize(approved)


def test_ask_approval_rejects_non_json_proposal_arguments():
    policy = DeterministicPolicy()
    policy.register("schedule", lambda args: {}, authority=AuthorityLevel.ASK)
    proposal = AIProposal(
        "bad-args", "qwen3", "schedule", {"unsafe": object()},
        capability=None,
    )

    import pytest
    with pytest.raises(ValueError, match="JSON-serializable"):
        policy.approve(proposal)
    assert not policy.authorize(proposal)
