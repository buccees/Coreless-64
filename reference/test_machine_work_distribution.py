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


def test_machine_exposes_unified_work_distribution():
    from machine_runtime import CorelessMachine
    machine = CorelessMachine(memory_size=4096)
    work_item = ComputeWork("machine-1", "cpu.step", AIRequest("request-1", "step", {"count": 1}))
    results = machine.distribute_work((work_item,))
    assert len(results) == 1
    assert results[0].work_id == "machine-1"
    assert results[0].result is not None
    assert results[0].resource_id == "cpu"

def test_machine_work_distribution_scales_to_resource_capacity():
    scheduler = MachineScheduler()
    scheduler.register(ConventionalComputeResource(
        "cpu-a", lambda w: ComputeResult(
            w.work_id, w.operation, "cpu", AIResult(w.request.request_id, "cpu", "done", {})
        ), capacity=3
    ))
    items = [work(f"w{i}") for i in range(3)]
    results = MachineWorkDistributor(scheduler).execute(items)
    assert all(result.result is not None for result in results)


def test_machine_work_distribution_single_item_fast_path():
    scheduler = MachineScheduler()
    scheduler.register(ConventionalComputeResource(
        "cpu", lambda w: ComputeResult(
            w.work_id, w.operation, "cpu", AIResult(w.request.request_id, "cpu", "done", {})
        ), capacity=1
    ))
    result = MachineWorkDistributor(scheduler).execute((work("one"),))
    assert result[0].resource_id == "cpu"
    assert scheduler.load("cpu") == 0


def test_machine_work_distribution_respects_ai_model_affinity_at_scale():
    scheduler = MachineScheduler()
    fabric = AIComputeFabric()
    barrier = threading.Barrier(2)
    fabric.register(FakeAI("qwen3", barrier))
    fabric.register(FakeAI("deepseek"))
    scheduler.register(AIComputeSchedulerResource(fabric, "qwen3", capacity=2))
    scheduler.register(AIComputeSchedulerResource(fabric, "deepseek", capacity=4))
    items = [
        ComputeWork(f"q{i}", "tensor.matmul",
                    AIRequest(f"r{i}", "compute", {}), model_id="qwen3")
        for i in range(2)
    ]
    results = MachineWorkDistributor(scheduler).execute(items)
    assert {result.resource_id for result in results} == {"ai:qwen3"}

def test_machine_work_distribution_empty_batch_has_no_scheduler_side_effects():
    scheduler = MachineScheduler()
    distributor = MachineWorkDistributor(scheduler)
    assert distributor.execute(()) == ()
