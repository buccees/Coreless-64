"""Fourteenth-wave system/control and translation conformance batch."""
import sys
sys.path.insert(0, ".")
import pytest
from core import CorelessCPU, CorelessTrap, USER, SUPERVISOR, MACHINE

def sysword(rd=0, rs1=0, f=0, operand=0):
    return (6 << 27) | (rd << 22) | (rs1 << 17) | ((operand & 0x7ff) << 5) | f

def test_nop_retires_without_architectural_state_change():
    cpu = CorelessCPU()
    cpu.pc = 0x40
    before = (cpu.cycle, cpu.instret, cpu.privilege)
    cpu.memory[0x40:0x44] = sysword(f=0).to_bytes(4, "little")
    assert cpu.step()
    assert cpu.pc == 0x44
    assert cpu.cycle == before[0] + 1
    assert cpu.instret == before[1] + 1
    assert cpu.privilege == before[2]

def test_halt_stops_subsequent_execution_and_retires_halt():
    cpu = CorelessCPU()
    cpu.memory[0:4] = sysword(f=1).to_bytes(4, "little")
    cpu.memory[4:8] = sysword(f=0).to_bytes(4, "little")
    assert cpu.step()
    assert cpu.halted is True
    assert cpu.pc == 4
    assert cpu.instret == 1
    assert cpu.step() is False
    assert cpu.pc == 4
    assert cpu.instret == 1

def test_wait_does_not_retire_or_advance_without_enabled_interrupt():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.csrs[0x001] = 1 << 3
    cpu.pending_interrupts = 0
    cpu.memory[0:4] = sysword(f=2).to_bytes(4, "little")
    before = (cpu.pc, cpu.cycle, cpu.instret)
    assert cpu.step()
    assert (cpu.pc, cpu.cycle, cpu.instret) == before

def test_wait_resumes_when_enabled_interrupt_is_pending():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.csrs[0x001] = 1 << 3
    cpu.pending_interrupts = 1 << 3
    cpu.csrs[0x002] = cpu.pending_interrupts
    cpu.csrs[0x003] = 0x200
    cpu.memory[0:4] = sysword(f=2).to_bytes(4, "little")
    assert cpu.step()
    assert cpu.pc == 0x200
    assert cpu.csrs[0x004] == 0

def test_trap_records_faulting_pc_and_tval_without_retirement():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.csrs[0x003] = 0x300
    cpu.memory[0:4] = sysword(f=3, operand=0x55).to_bytes(4, "little")
    assert cpu.step()
    assert cpu.pc == 0x300
    assert cpu.csrs[0x004] == 0
    assert (cpu.csrs[0x005] & 0x7F) == 0x005
    assert cpu.csrs[0x006] == 0x55
    assert cpu.instret == 0

def test_fence_is_an_architectural_retirement_point():
    cpu = CorelessCPU()
    cpu.pc = 0x20
    cpu.memory[0x20:0x24] = sysword(f=5, operand=0x155).to_bytes(4, "little")
    assert cpu.step()
    assert cpu.pc == 0x24
    assert cpu.instret == 1

def test_tlbflush_clears_all_cached_translations():
    cpu = CorelessCPU()
    cpu.tlb = {1: 0x1234, 7: 0x5678}
    cpu.memory[0:4] = sysword(f=6).to_bytes(4, "little")
    assert cpu.step()
    assert cpu.tlb == {}

def test_tlbflush_requires_machine_privilege():
    cpu = CorelessCPU()
    cpu.privilege = SUPERVISOR
    cpu.tlb = {1: 0x1234}
    cpu.csrs[0x003] = 0x400
    cpu.memory[0:4] = sysword(f=6).to_bytes(4, "little")
    cpu.step()
    assert cpu.pc == 0x400
    assert cpu.tlb == {1: 0x1234}
    assert (cpu.csrs[0x005] & 0x7F) == 0x004

def test_tlbflushva_invalidates_only_selected_page():
    cpu = CorelessCPU()
    cpu.tlb = {1: 0x1234, 2: 0x5678}
    cpu.r[1] = 0x2000
    cpu.memory[0:4] = sysword(rs1=1, f=7).to_bytes(4, "little")
    assert cpu.step()
    assert cpu.tlb == {1: 0x1234}

def test_tlbflushva_requires_machine_privilege():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.r[1] = 0x1000
    cpu.tlb = {1: 0x1234}
    cpu.csrs[0x003] = 0x500
    cpu.memory[0:4] = sysword(rs1=1, f=7).to_bytes(4, "little")
    cpu.step()
    assert cpu.pc == 0x500
    assert cpu.tlb == {1: 0x1234}
    assert (cpu.csrs[0x005] & 0x7F) == 0x004

def test_readcsr_and_writecsr_preserve_architectural_csr_semantics():
    cpu = CorelessCPU()
    cpu.r[1] = 0x12345678
    cpu.memory[0:4] = sysword(rs1=1, f=9, operand=0x01).to_bytes(4, "little")
    cpu.memory[4:8] = sysword(rd=2, f=8, operand=0x01).to_bytes(4, "little")
    assert cpu.step()
    assert cpu.step()
    assert cpu.r[2] == 0x12345678
