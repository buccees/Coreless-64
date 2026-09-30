from ai.compute_fabric import ComputeResult, ComputeWork, AIComputeFabric
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
    fabric = AIComputeFabric()
    fabric.register(ai)
    scheduler.register(AIComputeSchedulerResource(fabric, "qwen3"))
    result, allocation = scheduler.execute(work())
    assert result.model_id == "qwen3"
    assert allocation.kind == "ai"


def test_scheduler_falls_back_to_ai_when_conventional_resource_fails():
    scheduler = MachineScheduler()
    def broken(w):
        raise RuntimeError("conventional unavailable")
    scheduler.register(ConventionalComputeResource("cpu", broken))
    fabric = AIComputeFabric()
    fabric.register(FakeAI())
    scheduler.register(AIComputeSchedulerResource(fabric, "qwen3"))
    result, allocation = scheduler.execute(work("tensor.matmul"))
    assert result.model_id == "qwen3"
    assert allocation.fallback_used


def test_preference_can_explicitly_select_ai():
    scheduler = MachineScheduler()
    scheduler.register(ConventionalComputeResource(
        "cpu", lambda w: (_ for _ in ()).throw(AssertionError("CPU should not run"))))
    fabric = AIComputeFabric()
    fabric.register(FakeAI())
    scheduler.register(AIComputeSchedulerResource(fabric, "qwen3"))
    result, allocation = scheduler.execute(work(), preference="ai")
    assert allocation.kind == "ai"


def test_scheduler_exposes_live_load_during_execution():
    scheduler = MachineScheduler()
    observed = []

    def execute(w):
        observed.append(scheduler.load("cpu"))
        return ComputeResult(w.work_id, w.operation, "cpu",
                             AIResult(w.request.request_id, "cpu", "cpu", {}))

    scheduler.register(ConventionalComputeResource("cpu", execute, capacity=2))
    scheduler.execute(work("cpu.step"))
    assert observed == [1]
    assert scheduler.load("cpu") == 0


def test_scheduler_rejects_invalid_capacity():
    scheduler = MachineScheduler()
    try:
        scheduler.register(ConventionalComputeResource("cpu", lambda w: None, capacity=0))
    except ValueError as exc:
        assert "capacity" in str(exc)
    else:
        raise AssertionError("invalid capacity was accepted")


def test_scheduler_prefers_less_loaded_resource_deterministically():
    scheduler = MachineScheduler()
    observations = []

    def make_executor(resource_id):
        def execute(w):
            observations.append(resource_id)
            return ComputeResult(w.work_id, w.operation, resource_id,
                                 AIResult(w.request.request_id, resource_id, resource_id, {}))
        return execute

    scheduler.register(ConventionalComputeResource("cpu-a", make_executor("cpu-a"), capacity=2))
    scheduler.register(ConventionalComputeResource("cpu-b", make_executor("cpu-b"), capacity=2))

    scheduler.execute(work("cpu.step"))
    scheduler.execute(work("cpu.step"))

    assert observations == ["cpu-a", "cpu-a"]
    assert scheduler.load("cpu-a") == 0
    assert scheduler.load("cpu-b") == 0


def test_scheduler_uses_telemetry_to_choose_less_loaded_resource():
    from ai.telemetry import TelemetryProvider

    telemetry = TelemetryProvider()
    telemetry.publish(cpu={"cpu-a": 0.9, "cpu-b": 0.1})
    scheduler = MachineScheduler(telemetry=telemetry)
    scheduler.register(ConventionalComputeResource("cpu-a", lambda w: ComputeResult(
        w.work_id, w.operation, "cpu-a", AIResult(w.request.request_id, "cpu-a", "a", {})
    ), capacity=1))
    scheduler.register(ConventionalComputeResource("cpu-b", lambda w: ComputeResult(
        w.work_id, w.operation, "cpu-b", AIResult(w.request.request_id, "cpu-b", "b", {})
    ), capacity=1))

    result, allocation = scheduler.execute(work("cpu.step"))
    assert result.model_id == "cpu-b"
    assert allocation.resource_id == "cpu-b"
