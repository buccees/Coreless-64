from ai.compute_fabric import ComputeResult, ComputeWork, AIComputeFabric
from ai.interfaces import AIRequest, AIResult
import threading
from reference.machine_work_distribution import MachineWorkDistributor
from reference.scheduler import AIComputeSchedulerResource, ConventionalComputeResource, MachineScheduler


class FakeAI:
    def __init__(self, model_id, barrier=None):
        self.model_id = model_id
        self.barrier = barrier
    def compute(self, work):
        if self.barrier is not None:
            self.barrier.wait(timeout=5)
        return ComputeResult(work.work_id, work.operation, self.model_id,
                             AIResult(work.request.request_id, self.model_id, "ai", {}))


def work(work_id):
    return ComputeWork(work_id, "tensor.matmul", AIRequest(work_id, "compute", {}))


def test_machine_work_distribution_uses_multiple_resources():
    scheduler = MachineScheduler()
    fabric = AIComputeFabric()
    barrier = threading.Barrier(2)
    fabric.register(FakeAI("qwen3", barrier))
    fabric.register(FakeAI("deepseek", barrier))
    scheduler.register(AIComputeSchedulerResource(fabric, "qwen3"))
    scheduler.register(AIComputeSchedulerResource(fabric, "deepseek"))

    results = MachineWorkDistributor(scheduler, max_workers=2).execute(
        [work("w1"), work("w2")]
    )

    assert all(result.result is not None for result in results)
    assert {result.resource_id for result in results} == {"ai:qwen3", "ai:deepseek"}


def test_machine_work_distribution_preserves_input_order():
    scheduler = MachineScheduler()
    scheduler.register(ConventionalComputeResource(
        "cpu", lambda w: ComputeResult(
            w.work_id, w.operation, "cpu",
            AIResult(w.request.request_id, "cpu", "cpu", {})
        ), capacity=2
    ))

    results = MachineWorkDistributor(scheduler, max_workers=2).execute(
        [work("first"), work("second")]
    )

    assert tuple(result.work_id for result in results) == ("first", "second")
