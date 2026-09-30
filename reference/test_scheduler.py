from ai.compute_fabric import ComputeResult, ComputeWork
from ai.interfaces import AIRequest, AIResult
from reference.scheduler import AIComputeSchedulerResource, ConventionalComputeResource, MachineScheduler


class FakeAI:
    def __init__(self):
        self.calls = 0
        self.model_id = "qwen3"

    def compute(self, work):
        self.calls += 1
        return ComputeResult(work.work_id, work.operation, self.model_id,
                             AIResult(work.request.request_id, self.model_id, "ai", {}))


def work(operation="tensor.matmul"):
    return ComputeWork("w1", operation, AIRequest("r1", "compute", {}))


def test_scheduler_keeps_conventional_resource_available():
    scheduler = MachineScheduler()
    conventional = ConventionalComputeResource(
        "cpu", lambda w: ComputeResult(w.work_id, w.operation, "cpu", AIResult(
            w.request.request_id, "cpu", "cpu", {})))
    scheduler.register(conventional)
    result, allocation = scheduler.execute(work("cpu.step"))
    assert result.model_id == "cpu"
    assert allocation.kind == "conventional"
    assert scheduler.resources() == ("cpu",)


def test_scheduler_can_use_ai_as_native_compute_resource():
    scheduler = MachineScheduler()
    ai = FakeAI()
    scheduler.register(AIComputeSchedulerResource(ai, "qwen3"))
    result, allocation = scheduler.execute(work())
    assert result.model_id == "qwen3"
    assert allocation.kind == "ai"


def test_scheduler_falls_back_to_ai_when_conventional_resource_fails():
    scheduler = MachineScheduler()
    def broken(w):
        raise RuntimeError("conventional unavailable")
    scheduler.register(ConventionalComputeResource("cpu", broken))
    scheduler.register(AIComputeSchedulerResource(FakeAI(), "qwen3"))
    result, allocation = scheduler.execute(work("tensor.matmul"))
    assert result.model_id == "qwen3"
    assert allocation.fallback_used


def test_preference_can_explicitly_select_ai():
    scheduler = MachineScheduler()
    scheduler.register(ConventionalComputeResource(
        "cpu", lambda w: (_ for _ in ()).throw(AssertionError("CPU should not run"))))
    scheduler.register(AIComputeSchedulerResource(FakeAI(), "qwen3"))
    result, allocation = scheduler.execute(work(), preference="ai")
    assert allocation.kind == "ai"
