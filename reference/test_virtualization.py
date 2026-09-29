import sys;sys.path.insert(0,".")
import pytest
from virtualization import Hypervisor
def test_vm_lifecycle_and_interrupt():
    h=Hypervisor(4); vm=h.create_vm(1<<20,2); h.inject_interrupt(vm.vmid,7); h.run(vm.vmid)
    snap=h.snapshot(vm.vmid)
    assert vm.running and snap["vcpus"][1]["pc"]==0 and snap["pending_interrupts"]==[7]
    h.stop(vm.vmid); h.destroy_vm(vm.vmid); assert vm.vmid not in h.vms


def test_vcpus_in_same_vm_can_message_each_other():
    h = Hypervisor(2)
    vm = h.create_vm(1 << 20, 2)
    h.send_message(vm.vmid, 0, vm.vmid, 1, b"hello")
    assert h.recv_message(vm.vmid, 1) == b"hello"
    assert h.recv_message(vm.vmid, 1) is None


def test_vm_to_vm_message_requires_explicit_capability():
    h = Hypervisor(2)
    a = h.create_vm(1 << 20, 1)
    b = h.create_vm(1 << 20, 1)
    with pytest.raises(PermissionError):
        h.send_message(a.vmid, 0, b.vmid, 0, b"blocked")
    cap = h.grant_ipc(a.vmid, b.vmid)
    h.send_message(a.vmid, 0, b.vmid, 0, b"allowed", cap)
    assert h.recv_message(b.vmid, 0) == b"allowed"
    h.revoke_ipc(cap)
    with pytest.raises(PermissionError):
        h.send_message(a.vmid, 0, b.vmid, 0, b"blocked again", cap)


def test_ipc_capability_is_directional():
    h = Hypervisor(2)
    a = h.create_vm(1 << 20, 1)
    b = h.create_vm(1 << 20, 1)
    cap = h.grant_ipc(a.vmid, b.vmid)
    with pytest.raises(PermissionError):
        h.send_message(b.vmid, 0, a.vmid, 0, b"reverse", cap)


def test_shared_memory_requires_explicit_permissions():
    h = Hypervisor(2)
    a = h.create_vm(1 << 20, 1)
    b = h.create_vm(1 << 20, 1)
    with pytest.raises(PermissionError):
        h.check_shared_memory(b.vmid, a.vmid, b.vmid, 7)
    h.share_memory(a.vmid, b.vmid, 7, 1)
    assert h.check_shared_memory(b.vmid, a.vmid, b.vmid, 7)
    with pytest.raises(PermissionError):
        h.check_shared_memory(b.vmid, a.vmid, b.vmid, 7, write=True)
    h.share_memory(a.vmid, b.vmid, 7, 3)
    assert h.check_shared_memory(b.vmid, a.vmid, b.vmid, 7, write=True)
    h.revoke_shared_memory(a.vmid, b.vmid, 7)
    with pytest.raises(PermissionError):
        h.check_shared_memory(b.vmid, a.vmid, b.vmid, 7)



def test_destroy_vm_revokes_ipc_and_shared_memory():
    h = Hypervisor(2)
    a = h.create_vm(1 << 20, 1)
    b = h.create_vm(1 << 20, 1)
    cap = h.grant_ipc(a.vmid, b.vmid)
    h.share_memory(a.vmid, b.vmid, 9, 3)
    h.destroy_vm(a.vmid)
    assert cap not in h._ipc_caps
    assert all(a.vmid not in key[:2] for key in h._shared_regions)


def test_vcpu_state_snapshot_restore_preserves_isolated_state():
    h = Hypervisor(2)
    vm = h.create_vm(1 << 20, 1)
    h.set_vcpu_state(vm.vmid, 0, registers=[0, 7] + [0] * 30,
                     pc=0x1234, sp=0x8000, privilege=1, halted=True)
    state = h.snapshot_vcpu(vm.vmid, 0)
    h.set_vcpu_state(vm.vmid, 0, registers=[0] * 32, pc=0, sp=0,
                     privilege=0, halted=False)
    h.restore_vcpu(vm.vmid, 0, state)
    assert state["registers"][1] == 7
    assert h.snapshot_vcpu(vm.vmid, 0)["pc"] == 0x1234
    assert h.snapshot_vcpu(vm.vmid, 0)["privilege"] == 1
    assert h.snapshot_vcpu(vm.vmid, 0)["halted"] is True


def test_vcpu_state_rejects_invalid_register_file():
    h = Hypervisor(1)
    vm = h.create_vm(1 << 20, 1)
    with pytest.raises(ValueError):
        h.set_vcpu_state(vm.vmid, 0, registers=[0] * 31)


def test_vcpu_state_enforces_r0_zero():
    h = Hypervisor(1)
    vm = h.create_vm(1 << 20, 1)
    h.set_vcpu_state(vm.vmid, 0, registers=[9] * 32)
    assert h.snapshot_vcpu(vm.vmid, 0)["registers"][0] == 0


def test_interrupt_injection_isolated_per_vm():
    h = Hypervisor(2)
    a = h.create_vm(1 << 20, 1)
    b = h.create_vm(1 << 20, 1)
    h.inject_interrupt(a.vmid, 7)
    assert a.pending_interrupts == [7]
    assert b.pending_interrupts == []