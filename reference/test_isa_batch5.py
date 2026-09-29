"""Fifth-wave Coreless-64 system/interrupt conformance batch.

The cases below are derived directly from the concrete CSR/interrupt baseline
in specification/isa.md and the reference-machine implementation.
"""
import sys
sys.path.insert(0, ".")

import pytest

from core import CorelessCPU, CorelessTrap, USER, SUPERVISOR, HYPERVISOR, MACHINE


def test_defined_csr_privilege_matrix_matches_architecture():
    cpu = CorelessCPU()
    machine_only = (0x000, 0x001, 0x002, 0x003, 0x004, 0x005, 0x006, 0x007,
                    0x009, 0x01C, 0x01D, 0x01E)
    supervisor_min = (0x008, 0x015, 0x01A, 0x01B)
    hypervisor_min = (0x016, 0x017, 0x018, 0x019)
    user_visible = (0x00A, 0x00B, 0x00C, 0x00D, 0x00E, 0x00F, 0x010,
                    0x011, 0x012, 0x013, 0x014, 0x01F)

    for csr in machine_only:
        cpu.privilege = MACHINE
        cpu.read_csr(csr)
        for privilege in (USER, SUPERVISOR, HYPERVISOR):
            cpu.privilege = privilege
            with pytest.raises(CorelessTrap) as exc:
                cpu.read_csr(csr)
            assert exc.value.cause == "privilege_violation"

    for csr in supervisor_min:
        for privilege in (SUPERVISOR, HYPERVISOR, MACHINE):
            cpu.privilege = privilege
            cpu.read_csr(csr)
        cpu.privilege = USER
        with pytest.raises(CorelessTrap) as exc:
            cpu.read_csr(csr)
        assert exc.value.cause == "privilege_violation"

    for csr in hypervisor_min:
        for privilege in (HYPERVISOR, MACHINE):
            cpu.privilege = privilege
            cpu.read_csr(csr)
        for privilege in (USER, SUPERVISOR):
            cpu.privilege = privilege
            with pytest.raises(CorelessTrap) as exc:
                cpu.read_csr(csr)
            assert exc.value.cause == "privilege_violation"

    for csr in user_visible:
        cpu.privilege = USER
        cpu.read_csr(csr)


def test_read_only_csrs_reject_writes_as_illegal_csr():
    cpu = CorelessCPU()
    cpu.privilege = MACHINE
    for csr in (0x005, 0x00A, 0x00B, 0x00C, 0x00D, 0x00E, 0x00F, 0x016, 0x01F):
        with pytest.raises(CorelessTrap) as exc:
            cpu.write_csr(csr, 1)
        assert exc.value.cause == "illegal_csr"


def test_unknown_csr_is_illegal_not_privilege_violation():
    cpu = CorelessCPU()
    for privilege in (USER, SUPERVISOR, HYPERVISOR, MACHINE):
        cpu.privilege = privilege
        with pytest.raises(CorelessTrap) as exc:
            cpu.read_csr(0x3FF)
        assert exc.value.cause == "illegal_csr"


def test_interrupt_selection_uses_lowest_enabled_pending_bit():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.pc = 0x80
    cpu.csrs[0x003] = 0x400
    cpu.csrs[0x001] = (1 << 2) | (1 << 5) | (1 << 7)
    cpu.pending_interrupts = (1 << 5) | (1 << 2) | (1 << 9)
    cpu.csrs[0x002] = cpu.pending_interrupts

    assert cpu._take_interrupt_if_enabled() is True
    assert cpu.csrs[0x004] == 0x80
    assert (cpu.csrs[0x005] >> 63) == 1
    assert (cpu.csrs[0x005] & 0x7F) == 2
    assert cpu.pending_interrupts == ((1 << 5) | (1 << 9))
    assert cpu.csrs[0x002] == cpu.pending_interrupts


def test_disabled_pending_interrupt_does_not_enter_trap():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.pc = 0x80
    cpu.csrs[0x003] = 0x400
    cpu.csrs[0x001] = 1 << 3
    cpu.pending_interrupts = 1 << 7
    cpu.csrs[0x002] = cpu.pending_interrupts

    assert cpu._take_interrupt_if_enabled() is False
    assert cpu.pc == 0x80
    assert cpu.privilege == USER
    assert cpu.pending_interrupts == (1 << 7)


def test_interrupt_entry_saves_privilege_and_interrupt_enable_state():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.pc = 0x1234
    cpu.csrs[0x003] = 0x800
    cpu.csrs[0x001] = 0x14
    cpu.pending_interrupts = 1 << 4
    cpu.csrs[0x002] = cpu.pending_interrupts

    assert cpu._take_interrupt_if_enabled() is True
    assert cpu._trap_saved_privilege == USER
    assert cpu._trap_saved_ie == 0x14
    assert cpu.csrs[0x001] == 0
    assert cpu.privilege == SUPERVISOR
    assert cpu.csrs[0x000] == SUPERVISOR
    assert cpu.pc == 0x800


def test_machine_interrupt_keeps_machine_privilege():
    cpu = CorelessCPU()
    cpu.privilege = MACHINE
    cpu.pc = 0x100
    cpu.csrs[0x003] = 0x900
    cpu.csrs[0x001] = 1 << 1
    cpu.pending_interrupts = 1 << 1
    cpu.csrs[0x002] = cpu.pending_interrupts

    assert cpu._take_interrupt_if_enabled() is True
    assert cpu.privilege == MACHINE
    assert cpu.csrs[0x000] == MACHINE
    assert cpu.csrs[0x004] == 0x100


def test_retx_restores_interrupt_context_and_clears_selected_pending_bit():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.pc = 0x60
    cpu.csrs[0x003] = 0x700
    cpu.csrs[0x001] = 1 << 3
    cpu.pending_interrupts = 1 << 3
    cpu.csrs[0x002] = cpu.pending_interrupts

    assert cpu._take_interrupt_if_enabled() is True
    assert cpu.pending_interrupts == 0
    assert cpu.csrs[0x002] == 0

    next_pc = cpu._execute(("RETX",))
    assert next_pc == 0x60
    assert cpu.privilege == USER
    assert cpu.csrs[0x000] == USER
    assert cpu.csrs[0x001] == (1 << 3)


def test_interrupt_does_not_retire_or_advance_interrupted_instruction():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.pc = 0x100
    cpu.csrs[0x003] = 0x500
    cpu.csrs[0x001] = 1 << 1
    cpu.pending_interrupts = 1 << 1
    cpu.csrs[0x002] = cpu.pending_interrupts
    before_cycle = cpu.cycle
    before_instret = cpu.instret

    assert cpu.step() is True
    assert cpu.pc == 0x500
    assert cpu.cycle == before_cycle
    assert cpu.instret == before_instret


def test_interrupt_cause_contains_prior_privilege():
    cpu = CorelessCPU()
    cpu.privilege = HYPERVISOR
    cpu.pc = 0x240
    cpu.csrs[0x003] = 0xA00
    cpu.csrs[0x001] = 1 << 6
    cpu.pending_interrupts = 1 << 6
    cpu.csrs[0x002] = cpu.pending_interrupts

    assert cpu._take_interrupt_if_enabled() is True
    cause = cpu.csrs[0x005]
    assert ((cause >> 56) & 0x7F) == HYPERVISOR
    assert (cause & 0x7F) == 6
    assert (cause >> 63) == 1


def test_status_and_pending_csrs_track_interrupt_state():
    cpu = CorelessCPU()
    cpu.request_interrupt(5)
    assert cpu.read_csr(0x002) == (1 << 5)
    cpu.write_csr(0x002, 1 << 2)
    assert cpu.pending_interrupts == (1 << 2)
    assert cpu.read_csr(0x002) == (1 << 2)


def test_interrupt_entry_uses_tvec_and_preserves_epc_exactly():
    cpu = CorelessCPU()
    cpu.privilege = SUPERVISOR
    cpu.pc = 0x123456789ABC
    cpu.csrs[0x003] = 0xFEDC
    cpu.csrs[0x001] = 1
    cpu.pending_interrupts = 1
    cpu.csrs[0x002] = 1

    assert cpu._take_interrupt_if_enabled() is True
    assert cpu.csrs[0x004] == 0x123456789ABC
    assert cpu.pc == 0xFEDC
