"""Third-wave Coreless-64 CSR and interrupt conformance batch.

Expectations are derived directly from CSR_ACCESS and the concrete CSR/interrupt
baseline in specification/isa.md. These tests deliberately exercise the
architectural boundary rather than guessing Python implementation details.
"""
import sys
sys.path.insert(0, ".")

import pytest

from core import CorelessCPU, USER, SUPERVISOR, HYPERVISOR, MACHINE, CAUSE, CSR_ACCESS, CorelessTrap


def test_csr_contract_table_is_complete():
    assert set(CSR_ACCESS) == set(range(0x20))
    for csr, (name, access, privilege) in CSR_ACCESS.items():
        assert name
        assert access in ("r", "rw")
        assert privilege in (USER, SUPERVISOR, HYPERVISOR, MACHINE)


def test_user_can_read_user_csrs():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.csrs[0x00A] = 7
    cpu.csrs[0x00B] = 8
    cpu.csrs[0x00C] = 9
    cpu.csrs[0x01F] = 0x434C3634
    assert cpu.read_csr(0x00A) == 7
    assert cpu.read_csr(0x00B) == 8
    assert cpu.read_csr(0x00C) == 9
    assert cpu.read_csr(0x01F) == 0x434C3634


def test_lower_privilege_cannot_read_higher_privilege_csrs():
    for privilege, blocked in (
        (USER, (0x000, 0x008, 0x016)),
        (SUPERVISOR, (0x000, 0x016)),
        (HYPERVISOR, (0x000,)),
    ):
        cpu = CorelessCPU()
        cpu.privilege = privilege
        for csr in blocked:
            with pytest.raises(CorelessTrap) as exc:
                cpu.read_csr(csr)
            assert exc.value.cause == "privilege_violation"


def test_read_only_csr_write_is_an_illegal_csr():
    cpu = CorelessCPU()
    cpu.privilege = MACHINE
    for csr in (0x005, 0x00A, 0x00B, 0x00C, 0x00D, 0x00E, 0x00F, 0x016, 0x01D, 0x01F):
        with pytest.raises(CorelessTrap) as exc:
            cpu.write_csr(csr, 1)
        assert exc.value.cause == "illegal_csr"


def test_unknown_csr_is_illegal():
    cpu = CorelessCPU()
    cpu.privilege = MACHINE
    with pytest.raises(CorelessTrap) as exc:
        cpu.read_csr(0x20)
    assert exc.value.cause == "illegal_csr"


def test_csr_write_masks_to_64_bits():
    cpu = CorelessCPU()
    cpu.privilege = MACHINE
    cpu.write_csr(0x006, (1 << 80) | 0x55)
    assert cpu.csrs[0x006] == 0x55


def test_interrupt_takes_before_instruction_without_retiring_it():
    cpu = CorelessCPU()
    cpu.pc = 0x40
    cpu.csrs[0x003] = 0x100
    cpu.csrs[0x001] = (1 << 3)
    cpu.request_interrupt(3)
    cpu.memory[0x40:0x44] = ((6 << 27) | 0).to_bytes(4, "little")

    before = cpu.instret
    assert cpu.step()
    assert cpu.instret == before
    assert cpu.pc == 0x100
    assert cpu.csrs[0x004] == 0x40
    assert cpu.csrs[0x005] & (1 << 63)
    assert (cpu.csrs[0x005] & 0x7F) == 3
    assert cpu.privilege == SUPERVISOR
    assert cpu.csrs[0x001] == 0
    assert cpu.pending_interrupts == 0


def test_interrupt_selects_lowest_enabled_pending_bit():
    cpu = CorelessCPU()
    cpu.pc = 0x80
    cpu.csrs[0x003] = 0x200
    cpu.csrs[0x001] = (1 << 2) | (1 << 5)
    cpu.request_interrupt(5)
    cpu.request_interrupt(2)
    assert cpu._take_interrupt_if_enabled()
    assert (cpu.csrs[0x005] & 0x7F) == 2
    assert cpu.pending_interrupts == (1 << 5)


def test_retx_restores_interrupted_pc_privilege_and_interrupt_enable():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.csrs[0x001] = 0x21
    cpu.csrs[0x003] = 0x100
    cpu.pc = 0x40
    cpu.request_interrupt(0)
    assert cpu._take_interrupt_if_enabled()
    cpu.memory[0x100:0x104] = ((6 << 27) | 4).to_bytes(4, "little")
    assert cpu.step()
    assert cpu.pc == 0x40
    assert cpu.privilege == USER
    assert cpu.csrs[0x001] == 0x21


def test_interrupt_cause_is_distinguishable_from_synchronous_cause():
    cpu = CorelessCPU()
    cpu.csrs[0x003] = 0x100
    cpu.csrs[0x001] = 1
    cpu.request_interrupt(0)
    cpu.step()
    assert cpu.csrs[0x005] & (1 << 63)
    assert (cpu.csrs[0x005] & 0x7F) == 0
    assert CAUSE["illegal_instruction"] == 0x002
