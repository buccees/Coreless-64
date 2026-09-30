from ai.collaboration import DeterministicCollaboration
from ai.interfaces import AIProposal, AIRequest, AIResult


def proposal(model: str, operation: str = "schedule") -> AIProposal:
    return AIProposal(
        proposal_id=f"{model}-p",
        source_model=model,
        operation=operation,
        arguments={"cpu": 1},
    )


def result(model: str, p: AIProposal) -> AIResult:
    return AIResult(
        request_id="r1",
        model_id=model,
        text="analysis",
        metadata={"proposal": p},
    )


def test_consensus_produces_one_deterministic_recommendation():
    request = AIRequest(request_id="r1", prompt="schedule workload")
    results = tuple(result(m, proposal(m)) for m in ("qwen3", "deepseek", "gpt-oss"))

    group = DeterministicCollaboration().deliberate(request, results)

    assert group.participants == ("qwen3", "deepseek", "gpt-oss")
    assert group.recommended_action == results[0].metadata["proposal"]
    assert group.authorization_required is True
    assert group.confidence == 1.0


def test_conflicting_proposals_do_not_select_an_action():
    request = AIRequest(request_id="r1", prompt="schedule workload")
    results = (
        result("qwen3", proposal("qwen3", "schedule")),
        result("deepseek", proposal("deepseek", "migrate")),
    )

    group = DeterministicCollaboration().deliberate(request, results)

    assert group.recommended_action is None
    assert group.disagreements
    assert "no consensus" in group.resolution


def test_unstructured_ai_text_never_becomes_a_proposal():
    request = AIRequest(request_id="r1", prompt="inspect system")
    results = (
        AIResult(request_id="r1", model_id="qwen3", text="execute this"),
        AIResult(request_id="r1", model_id="deepseek", text="do it"),
    )

    group = DeterministicCollaboration().deliberate(request, results)

    assert group.proposals == ()
    assert group.recommended_action is None
    assert group.authorization_required is True
