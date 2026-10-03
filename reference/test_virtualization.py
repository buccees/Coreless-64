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

def test_multiple_native_cpus_bind_and_step_independent_vcpus():
    from core import CorelessCPU
    h = Hypervisor(2)
    vm = h.create_vm(1 << 16, 2)
    cpu0 = CorelessCPU(memory_size=1 << 16)
    cpu1 = CorelessCPU(memory_size=1 << 16, memory=cpu0.memory)
    h.bind_cpu(vm.vmid, cpu0, 0)
    h.bind_cpu(vm.vmid, cpu1, 1)
    cpu0.memory[0:4] = ((1 << 27) | (1 << 22) | 3).to_bytes(4, "little")
    cpu1.memory[0:4] = ((1 << 27) | (2 << 22) | 7).to_bytes(4, "little")
    h.run(vm.vmid)
    assert h.bound_cpu(vm.vmid, 0) is cpu0
    assert h.bound_cpu(vm.vmid, 1) is cpu1
    assert h.step(vm.vmid, vcpu_id=0) == 1
    assert h.step(vm.vmid, vcpu_id=1) == 1
    assert h.snapshot_vcpu(vm.vmid, 0)["registers"][1] == 3
    assert h.snapshot_vcpu(vm.vmid, 1)["registers"][2] == 7


def vmword(f, rd=0, rs1=0, rs2=0):
    return (12 << 27) | (rd << 22) | (rs1 << 17) | (rs2 << 12) | f

def test_vm_instruction_encoding_decodes_concrete_operations():
    from encoding import decode, VM
    for f, name in VM.items():
        assert decode(vmword(f)) == (name, 0, 0, 0)

def test_vm_instruction_requires_hypervisor_privilege_and_handler():
    from core import CorelessCPU, USER, HYPERVISOR
    cpu = CorelessCPU()
    cpu.memory[0:4] = vmword(0).to_bytes(4, "little")
    cpu.privilege = USER
    cpu.csrs[0x003] = 0x400
    cpu.step()
    assert cpu.pc == 0x400
    assert (cpu.csrs[0x005] & 0x7F) == 0x012
    cpu.reset()
    cpu.memory[0:4] = vmword(0).to_bytes(4, "little")
    cpu.privilege = HYPERVISOR
    cpu.csrs[0x003] = 0x500
    cpu.step()
    assert cpu.pc == 0x500
    assert (cpu.csrs[0x005] & 0x7F) == 0x012

def test_vm_instruction_dispatches_to_hypervisor_handler():
    from core import CorelessCPU, HYPERVISOR
    cpu = CorelessCPU()
    cpu.privilege = HYPERVISOR
    cpu.r[1] = 7
    cpu.r[2] = 9
    seen = []
    def handler(machine, op, rd, rs1, rs2):
        seen.append((op, rd, rs1, rs2, machine.read_reg(rs1), machine.read_reg(rs2)))
        return 0x55
    cpu.vm_handler = handler
    cpu.memory[0:4] = vmword(0, rd=3, rs1=1, rs2=2).to_bytes(4, "little")
    assert cpu.step()
    assert seen == [("VM_SEND", 3, 1, 2, 7, 9)]
    assert cpu.r[3] == 0x55


def test_vm_rejects_unshared_native_cpu_memory():
    from core import CorelessCPU
    h = Hypervisor(2)
    vm = h.create_vm(1 << 16, 2)
    cpu0 = CorelessCPU(memory_size=1 << 16)
    cpu1 = CorelessCPU(memory_size=1 << 16)
    h.bind_cpu(vm.vmid, cpu0, 0)
    with pytest.raises(ValueError):
        h.bind_cpu(vm.vmid, cpu1, 1)


def test_bound_native_cpu_retires_and_syncs_vcpu_state():
    from core import CorelessCPU
    h = Hypervisor(1)
    vm = h.create_vm(1 << 16, 1)
    cpu = CorelessCPU(memory_size=1 << 16)
    h.bind_cpu(vm.vmid, cpu)
    cpu.memory[0:4] = ((1 << 27) | (1 << 22) | 5).to_bytes(4, "little")
    h.run(vm.vmid)
    assert h.step(vm.vmid) == 1
    assert h.snapshot_vcpu(vm.vmid, 0)["registers"][1] == 5
    assert h.snapshot_vcpu(vm.vmid, 0)["pc"] == 4


def test_bound_cpu_initializes_from_vcpu_state():
    from core import CorelessCPU
    h = Hypervisor(1)
    vm = h.create_vm(1 << 16, 1)
    h.set_vcpu_state(vm.vmid, 0, registers=[0, 9] + [0] * 30,
                     pc=0x20, sp=0x8000, privilege=3, halted=False)
    cpu = CorelessCPU(memory_size=1 << 16)
    h.bind_cpu(vm.vmid, cpu)
    assert cpu.r[1] == 9
    assert cpu.pc == 0x20
    assert cpu.sp == 0x8000
    assert cpu.privilege == 3


def test_bound_cpu_can_be_resynchronized_from_vm_state():
    from core import CorelessCPU
    h = Hypervisor(1)
    vm = h.create_vm(1 << 16, 1)
    cpu = CorelessCPU(memory_size=1 << 16)
    h.bind_cpu(vm.vmid, cpu)
    h.set_vcpu_state(vm.vmid, 0, registers=[0, 17] + [0] * 30,
                     pc=0x40, sp=0x9000, privilege=2, halted=True)
    h.sync_cpu(vm.vmid)
    assert cpu.r[1] == 17
    assert cpu.pc == 0x40
    assert cpu.sp == 0x9000
    assert cpu.privilege == 2
    assert cpu.halted is True
