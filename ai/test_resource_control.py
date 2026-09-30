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


def test_authorized_vm_operation_reaches_reference_hypervisor():
    from reference.virtualization import Hypervisor

    policy = DeterministicPolicy()
    hypervisor = Hypervisor(cpu_count=1)
    vm = hypervisor.create_vm(4096)
    controller = CorelessResourceController(policy, hypervisor=hypervisor)
    controller.register_defaults()
    controller.grant("vm.start", "cap-vm")
    p = AIProposal("p2", "qwen3", "vm.start", {"vmid": vm.vmid}, capability="cap-vm")
    assert controller.execute(p) == {"vmid": vm.vmid, "running": True}
    assert hypervisor.vms[vm.vmid].running is True


def test_revoked_resource_capability_blocks_reference_control():
    from reference.virtualization import Hypervisor

    policy = DeterministicPolicy()
    hypervisor = Hypervisor(cpu_count=1)
    vm = hypervisor.create_vm(4096)
    controller = CorelessResourceController(policy, hypervisor=hypervisor)
    controller.register_defaults()
    controller.grant("vm.start", "cap-vm")
    policy.revoke_capability("cap-vm")
    p = AIProposal("p3", "qwen3", "vm.start", {"vmid": vm.vmid}, capability="cap-vm")
    try:
        controller.execute(p)
    except PermissionError:
        pass
    else:
        raise AssertionError("revoked capability must block VM control")
    assert hypervisor.vms[vm.vmid].running is False


class Memory:
    def __init__(self):
        self.data = bytearray(32)
        self.flushed = False
    def __getitem__(self, key):
        return self.data[key]
    def __setitem__(self, key, value):
        self.data[key] = value
    def flush(self):
        self.flushed = True


def test_authorized_memory_write_reaches_bound_memory():
    memory = Memory()
    policy = DeterministicPolicy()
    controller = CorelessResourceController(policy, memory=memory, compute=Compute())
    controller.register_defaults()
    controller.grant("memory.write", "cap-memory")
    p = AIProposal("p4", "qwen3", "memory.write", {"address": 4, "data": b"abc"}, capability="cap-memory")
    assert controller.execute(p) == {"written": 3}
    assert bytes(memory.data[4:7]) == b"abc"
    assert memory.flushed is True
