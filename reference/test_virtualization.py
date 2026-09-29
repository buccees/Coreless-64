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
