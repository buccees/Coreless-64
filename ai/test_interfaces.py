from ai.interfaces import (
    AIProposal,
    AIRequest,
    AIResult,
    AuthorityLevel,
    GroupResult,
)


def test_ai_request_defaults_to_recommendation_authority():
    request = AIRequest(request_id="r1", prompt="inspect system")
    assert request.authority is AuthorityLevel.RECOMMEND


def test_group_result_can_hold_multiple_ai_cores_and_one_recommendation():
    proposal = AIProposal(
        proposal_id="p1",
        source_model="qwen3",
        operation="schedule",
        arguments={"cpu": 1},
    )
    result = GroupResult(
        request_id="r1",
        participants=("qwen3", "deepseek", "gpt-oss"),
        proposals=(proposal,),
        agreements=("workload is CPU-bound",),
        resolution="schedule on an available CPU",
        recommended_action=proposal,
    )
    assert result.participants == ("qwen3", "deepseek", "gpt-oss")
    assert result.recommended_action is proposal
    assert result.authorization_required is True


def test_ai_result_is_transport_data_not_authorization():
    result = AIResult(request_id="r1", model_id="gpt-oss", text="execute it")
    assert result.text == "execute it"
    assert not hasattr(result, "authorization")
