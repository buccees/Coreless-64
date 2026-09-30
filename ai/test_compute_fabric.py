from ai.compute_fabric import AIComputeFabric, ComputeWork, RegisteredAICoreResource
from ai.interfaces import AIRequest, AIResult
from ai.registry import AICoreRegistry


class FakeCore:
    model_id = "qwen3"

    def infer(self, request):
        return AIResult(
            model_id=self.model_id,
            request_id=request.request_id,
            output_text="computed",
            metadata={"role": "compute"},
        )


def test_ai_core_can_be_exposed_as_compute_resource():
    registry = AICoreRegistry()
    registry.register(FakeCore())
    fabric = AIComputeFabric()
    fabric.register(RegisteredAICoreResource(registry, "qwen3"))

    work = ComputeWork(
        "w1",
        "tensor.matmul",
        AIRequest("r1", "compute this", {"shape": [2, 2]}),
    )
    result = fabric.compute(work, "qwen3")

    assert result.work_id == "w1"
    assert result.operation == "tensor.matmul"
    assert result.model_id == "qwen3"
    assert result.result.output_text == "computed"


def test_compute_resource_is_explicitly_registered():
    fabric = AIComputeFabric()
    try:
        fabric.compute(
            ComputeWork("w1", "noop", AIRequest("r1", "x", {})),
            "missing",
        )
    except KeyError:
        pass
    else:
        raise AssertionError("unregistered AI compute must fail")
