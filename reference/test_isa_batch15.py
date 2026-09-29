"""Fifteenth-wave capability discovery and architectural counter conformance."""
import sys
sys.path.insert(0, ".")

import pytest

from core import CorelessCPU, CorelessTrap, USER, SUPERVISOR, MACHINE


def test_user_capability_csrs_are_readable():
    cpu = CorelessCPU()
    cpu.privilege = USER
    assert cpu.read_csr(0x00A) == 0
    assert cpu.read_csr(0x00B) == 1
    assert cpu.read_csr(0x00C) == 0
    assert cpu.read_csr(0x01F) == 0x434C3634


def test_architecture_id_is_64_bit_coreless_identifier():
    cpu = CorelessCPU()
    assert cpu.read_csr(0x01F) == int.from_bytes(b"CL64", "big")


def test_cpu_count_and_id_are_stable_capability_values():
    cpu = CorelessCPU()
    cpu.privilege = USER
    assert cpu.read_csr(0x00A) == 0
    assert cpu.read_csr(0x00B) == 1


def test_capability_base_is_user_readable():
    cpu = CorelessCPU()
    cpu.privilege = USER
    assert cpu.read_csr(0x00C) == 0


def test_time_cycle_and_instret_are_architectural_counters():
    cpu = CorelessCPU()
    cpu.privilege = USER
    assert cpu.read_csr(0x00D) == 0
    assert cpu.read_csr(0x00E) == 0
    assert cpu.read_csr(0x00F) == 0
    cpu.cycle = 17
    cpu.instret = 9
    assert cpu.read_csr(0x00D) == 17
    assert cpu.read_csr(0x00E) == 17
    assert cpu.read_csr(0x00F) == 9


def test_user_cannot_write_read_only_capability_csrs():
    cpu = CorelessCPU()
    cpu.privilege = USER
    for csr in (0x00A, 0x00B, 0x00C, 0x00D, 0x00E, 0x00F, 0x01F):
        with pytest.raises(CorelessTrap) as exc:
            cpu.write_csr(csr, 0x1234)
        assert exc.value.cause == "privilege_violation" if csr in (0x00A, 0x00B, 0x00C, 0x00D, 0x00E, 0x00F, 0x01F) else True


def test_machine_configuration_is_privileged_and_writable():
    cpu = CorelessCPU()
    cpu.privilege = SUPERVISOR
    with pytest.raises(CorelessTrap) as exc:
        cpu.write_csr(0x01E, 0x1234)
    assert exc.value.cause == "privilege_violation"
    cpu.privilege = MACHINE
    cpu.write_csr(0x01E, 0x1234)
    assert cpu.read_csr(0x01E) == 0x1234


def test_hypervisor_state_csrs_require_hypervisor_privilege():
    cpu = CorelessCPU()
    for privilege in (USER, SUPERVISOR):
        cpu.privilege = privilege
        for csr in (0x016, 0x017, 0x018, 0x019):
            with pytest.raises(CorelessTrap) as exc:
                cpu.read_csr(csr)
            assert exc.value.cause == "privilege_violation"


def test_supervisor_translation_csrs_require_supervisor_privilege():
    cpu = CorelessCPU()
    for privilege in (USER,):
        cpu.privilege = privilege
        for csr in (0x008, 0x015, 0x01A, 0x01B):
            with pytest.raises(CorelessTrap) as exc:
                cpu.read_csr(csr)
            assert exc.value.cause == "privilege_violation"


def test_architectural_counter_reads_do_not_modify_state():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.cycle = 23
    cpu.instret = 11
    before = (cpu.cycle, cpu.instret)
    values = [cpu.read_csr(csr) for csr in (0x00D, 0x00E, 0x00F)]
    assert values == [23, 23, 11]
    assert (cpu.cycle, cpu.instret) == before
