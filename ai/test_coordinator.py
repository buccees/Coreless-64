from ai.coordinator import NestCoordinator
from ai.interfaces import AIProposal, AIRequest, AIResult
from ai.registry import AICoreRegistry


class FakeCore:
    def __init__(self, model_id: str, operation: str = "schedule", fail: bool = False):
        self._model_id = model_id
        self._operation = operation
        self._fail = fail

    @property
    def model_id(self) -> str:
        return self._model_id

    def infer(self, request: AIRequest) -> AIResult:
        if self._fail:
            raise RuntimeError("core unavailable")
        proposal = AIProposal(
            proposal_id=f"{self._model_id}-p",
            source_model=self._model_id,
            operation=self._operation,
            arguments={"cpu": 1},
        )
        return AIResult(
            request_id=request.request_id,
            model_id=self._model_id,
            text="analysis",
            metadata={"proposal": proposal},
        )


def test_coordinator_runs_multiple_cores_and_produces_one_group_result():
    registry = AICoreRegistry()
    for model in ("qwen3", "deepseek", "gpt-oss"):
        registry.register(FakeCore(model))

    result = NestCoordinator(registry).coordinate(
        AIRequest("r1", "schedule workload")
    )

    assert tuple(r.model_id for r in result.results) == (
        "qwen3",
        "deepseek",
        "gpt-oss",
    )
    assert result.group.recommended_action is not None
    assert result.group.authorization_required is True
    assert result.failures == ()


def test_one_failed_core_does_not_stop_the_other_cores():
    registry = AICoreRegistry()
    registry.register(FakeCore("qwen3"))
    registry.register(FakeCore("deepseek", fail=True))
    registry.register(FakeCore("gpt-oss"))

    result = NestCoordinator(registry).coordinate(
        AIRequest("r1", "inspect system")
    )

    assert tuple(r.model_id for r in result.results) == ("qwen3", "gpt-oss")
    assert len(result.failures) == 1
    assert result.failures[0].model_id == "deepseek"


def test_conflicting_cores_reach_collaboration_without_auto_selection():
    registry = AICoreRegistry()
    registry.register(FakeCore("qwen3", "schedule"))
    registry.register(FakeCore("deepseek", "migrate"))

    result = NestCoordinator(registry).coordinate(
        AIRequest("r1", "choose an operation")
    )

    assert result.group.recommended_action is None
    assert result.group.disagreements
