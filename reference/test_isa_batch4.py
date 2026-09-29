"""Fourth-wave Coreless-64 privileged execution conformance batch.

These tests cover the concrete v0.x system/privilege/trap rules already defined
in specification/isa.md. They intentionally test architectural state and
retirement behavior rather than implementation details.
"""
import sys
sys.path.insert(0, ".")

import pytest

from core import CorelessCPU, USER, SUPERVISOR, HYPERVISOR, MACHINE, CorelessTrap


def test_status_csr_tracks_current_privilege():
    cpu = CorelessCPU()
    assert cpu.read_csr(0x000) == MACHINE
    cpu.privilege = USER
    assert cpu.read_csr(0x000) == USER
    cpu.privilege = SUPERVISOR
    assert cpu.read_csr(0x000) == SUPERVISOR


def test_status_write_changes_privilege_and_status():
    cpu = CorelessCPU()
    cpu.write_csr(0x000, USER)
    assert cpu.privilege == USER
    assert cpu.csrs[0x000] == USER
    assert cpu.read_csr(0x000) == USER


def test_pending_interrupt_csr_is_live_state():
    cpu = CorelessCPU()
    cpu.request_interrupt(4)
    assert cpu.read_csr(0x002) == (1 << 4)
    cpu.write_csr(0x002, 0x20)
    assert cpu.pending_interrupts == 0x20
    assert cpu.read_csr(0x002) == 0x20


def test_synchronous_trap_records_prior_privilege_in_cause():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.csrs[0x003] = 0x300
    cpu._enter_trap(CorelessTrap("breakpoint", 0x40, 0x77))
    assert cpu.csrs[0x004] == 0x40
    assert (cpu.csrs[0x005] >> 56) & 0x7F == USER
    assert (cpu.csrs[0x005] & 0x7F) == 0x005
    assert cpu.csrs[0x006] == 0x77
    assert cpu.privilege == SUPERVISOR
    assert cpu.csrs[0x001] == 0


def test_trap_entry_does_not_retire_faulting_instruction():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.csrs[0x003] = 0x200
    cpu.csrs[0x001] = 0x55
    before = cpu.instret
    before_cycle = cpu.cycle
    cpu._enter_trap(CorelessTrap("illegal_instruction", 0x80, 0x1234))
    assert cpu.instret == before
    assert cpu.cycle == before_cycle
    assert cpu.pc == 0x200
    assert cpu.csrs[0x004] == 0x80


def test_retx_restores_saved_state_exactly():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.csrs[0x001] = 0x2A
    cpu.csrs[0x003] = 0x500
    cpu.pc = 0x44
    cpu._enter_trap(CorelessTrap("breakpoint", 0x44, 9))
    assert cpu.privilege == SUPERVISOR
    cpu._execute(("RETX",))
    assert cpu.privilege == USER
    assert cpu.csrs[0x000] == USER
    assert cpu.csrs[0x001] == 0x2A
    assert cpu.pc == 0x44


def test_retx_is_rejected_from_user_mode():
    cpu = CorelessCPU()
    cpu.privilege = USER
    with pytest.raises(CorelessTrap) as exc:
        cpu._execute(("RETX",))
    assert exc.value.cause == "privilege_violation"


def test_tlbflush_is_machine_only():
    for privilege in (USER, SUPERVISOR, HYPERVISOR):
        cpu = CorelessCPU()
        cpu.privilege = privilege
        cpu.tlb[7] = 0x123
        with pytest.raises(CorelessTrap) as exc:
            cpu._execute(("TLBFLUSH",))
        assert exc.value.cause == "privilege_violation"
        assert cpu.tlb[7] == 0x123


def test_tlbflush_clears_all_cached_translations_in_machine_mode():
    cpu = CorelessCPU()
    cpu.tlb.update({1: 0x101, 9: 0x909, 31: 0x3131})
    cpu._execute(("TLBFLUSH",))
    assert cpu.tlb == {}


def test_tlbflushva_only_removes_selected_page():
    cpu = CorelessCPU()
    cpu.r[3] = 0x2345
    cpu.tlb.update({2: 0x222, 9: 0x999})
    cpu._execute(("TLBFLUSHVA", 3))
    assert 2 not in cpu.tlb
    assert cpu.tlb[9] == 0x999


def test_tlbflushva_preserves_other_entries_when_privileged():
    cpu = CorelessCPU()
    cpu.privilege = SUPERVISOR
    cpu.r[3] = 0x2000
    cpu.tlb[2] = 0x222
    with pytest.raises(CorelessTrap) as exc:
        cpu._execute(("TLBFLUSHVA", 3))
    assert exc.value.cause == "privilege_violation"
    assert cpu.tlb[2] == 0x222


def test_hypervisor_and_machine_csr_boundaries_are_enforced():
    for privilege, csr in (
        (USER, 0x016),
        (SUPERVISOR, 0x016),
        (SUPERVISOR, 0x000),
        (HYPERVISOR, 0x000),
    ):
        cpu = CorelessCPU()
        cpu.privilege = privilege
        with pytest.raises(CorelessTrap) as exc:
            cpu.read_csr(csr)
        assert exc.value.cause == "privilege_violation"


def test_arch_id_is_stable_and_user_visible():
    cpu = CorelessCPU()
    cpu.privilege = USER
    assert cpu.read_csr(0x01F) == 0x434C3634
