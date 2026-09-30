from ai.interfaces import AIProposal, AuthorityLevel
from ai.policy import DeterministicPolicy
from ai.resource_control import CorelessResourceController


class Compute:
    def submit(self, operation, payload):
        self.last = (operation, payload)
        return "job-1"


def test_policy_bound_compute_operation_reaches_compute_interface():
    compute = Compute()
    policy = DeterministicPolicy()
    controller = CorelessResourceController(policy, compute=compute)
    controller.register_defaults()
    controller.grant("compute.submit", "cap-compute")
    p = AIProposal(
        "p1", "qwen3", "compute.submit",
        {"operation": "vector", "payload": {"count": 4}},
        capability="cap-compute",
    )
    assert controller.execute(p) == {"job_id": "job-1"}
    assert compute.last == ("vector", {"count": 4})


def test_missing_capability_stops_before_resource_access():
    compute = Compute()
    policy = DeterministicPolicy()
    controller = CorelessResourceController(policy, compute=compute)
    controller.register_defaults()
    p = AIProposal(
        "p1", "qwen3", "compute.submit",
        {"operation": "vector"},
    )
    try:
        controller.execute(p)
    except PermissionError:
        pass
    else:
        raise AssertionError("missing capability must be denied")
    assert not hasattr(compute, "last")


def test_resource_controller_does_not_register_unavailable_resources():
    policy = DeterministicPolicy()
    controller = CorelessResourceController(policy)
    try:
        controller.register_defaults()
    except ValueError:
        pass
    else:
        raise AssertionError("compute is required for default registration")
