from ai.interfaces import AIRequest, AIResult
from ai.registry import AICoreRegistry
from ai.work_distribution import WorkDistributor, WorkItem


class FakeCore:
    def __init__(self, model_id: str, fail: bool = False):
        self._model_id = model_id
        self.fail = fail
        self.calls = 0

    @property
    def model_id(self) -> str:
        return self._model_id

    def infer(self, request: AIRequest) -> AIResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("offline")
        return AIResult(request.request_id, self._model_id, request.prompt)


def item(number: int) -> WorkItem:
    return WorkItem(work_id=f"w{number}", request=AIRequest(f"r{number}", f"work {number}"))


def test_work_is_split_across_all_enabled_cores():
    registry = AICoreRegistry()
    cores = [FakeCore(name) for name in ("qwen3", "deepseek", "gpt-oss")]
    for core in cores:
        registry.register(core)
    results = WorkDistributor(registry).execute(tuple(item(i) for i in range(6)))
    assert all(result.result is not None for result in results)
    assert sum(core.calls for core in cores) == 6
    assert {result.result.model_id for result in results} == {"qwen3", "deepseek", "gpt-oss"}


def test_idle_cores_absorb_extra_work_dynamically():
    registry = AICoreRegistry()
    cores = [FakeCore(name) for name in ("qwen3", "deepseek", "gpt-oss")]
    for core in cores:
        registry.register(core)
    results = WorkDistributor(registry).execute(tuple(item(i) for i in range(12)))
    assert all(result.result is not None for result in results)
    assert sum(core.calls for core in cores) == 12
    assert all(core.calls > 1 for core in cores)


def test_failed_core_work_is_reassigned_to_healthy_cores():
    registry = AICoreRegistry()
    failed = FakeCore("qwen3", fail=True)
    healthy_a = FakeCore("deepseek")
    healthy_b = FakeCore("gpt-oss")
    for core in (failed, healthy_a, healthy_b):
        registry.register(core)
    results = WorkDistributor(registry).execute(tuple(item(i) for i in range(6)))
    assert all(result.result is not None for result in results)
    assert all(result.result.model_id != "qwen3" for result in results)
    assert healthy_a.calls + healthy_b.calls >= 6


def test_all_cores_can_execute_work_without_specialty_lock_in():
    registry = AICoreRegistry()
    registry.register(FakeCore("gemma"))
    registry.register(FakeCore("codestral"))
    results = WorkDistributor(registry).execute((item(1), item(2)))
    assert {result.result.model_id for result in results} == {"gemma", "codestral"}

def test_max_workers_limits_concurrency_without_disabling_cores():
    registry = AICoreRegistry()
    for model in ("a", "b", "c"):
        registry.register(Core(model))
    distributor = WorkDistributor(registry, max_workers=1)
    items = [WorkItem(str(i), AIRequest(str(i), "x", {})) for i in range(3)]
    results = distributor.execute(items)
    assert len(results) == 3
    assert all(item.result is not None for item in results)


def test_work_distribution_can_be_cancelled():
    registry = AICoreRegistry()
    registry.register(Core("a"))
    distributor = WorkDistributor(registry)
    items = [WorkItem("1", AIRequest("1", "x", {}))]
    results = distributor.execute(items, cancelled=lambda: True)
    assert results == ()
