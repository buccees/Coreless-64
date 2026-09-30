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
    assert policy.authorize(proposal()) is True
    assert policy.execute(proposal()) == {"scheduled": 1}


def test_ask_requires_explicit_approval():
    policy = DeterministicPolicy()
    p = proposal()
    policy.register("schedule", lambda args: {"ok": True}, authority=AuthorityLevel.ASK)
    assert policy.authorize(p) is False
    policy.approve("p1")
    assert policy.authorize(p) is True
    policy.revoke_approval("p1")
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
    assert policy.execute(proposal(operation="safe_stop")) == {"state": "safe"}
