"""Sixth-wave Coreless-64 scalar execution conformance batch.

This batch validates the concrete base integer, memory, control-flow, and
architectural-state rules already implemented by the reference machine.
"""
import sys
sys.path.insert(0, ".")

import pytest

from core import CorelessCPU, CorelessTrap, MASK64
from isa_expect import scalar_binary, branch_target, jump_target, aligned_memory_size\nfrom isa_expect import (\n    scalar_binary, immediate, branch_target, jump_target, effective_address,\n    aligned_memory_size,\n)


def test_r0_is_hardwired_zero():
    cpu = CorelessCPU()
    cpu.r[0] = 123
    cpu.write_reg(0, MASK64)
    assert cpu.read_reg(0) == 0
    assert cpu.r[0] == 123
    cpu._execute(("ADD", 0, 1, 2))
    assert cpu.read_reg(0) == 0


def test_integer_arithmetic_wraps_to_64_bits():
    cpu = CorelessCPU()
    cpu.r[1] = MASK64
    cpu.r[2] = 1
    cpu._execute(("ADD", 3, 1, 2))
    assert cpu.r[3] == scalar_binary("ADD", MASK64, 1)

    cpu.r[1] = 0
    cpu.r[2] = 1
    cpu._execute(("SUB", 3, 1, 2))
    assert cpu.r[3] == scalar_binary("SUB", 0, 1)

    cpu.r[1] = MASK64
    cpu.r[2] = 2
    cpu._execute(("MUL", 3, 1, 2))
    assert cpu.r[3] == scalar_binary("MUL", MASK64, 2)


def test_signed_and_unsigned_division_and_remainder():
    cpu = CorelessCPU()
    cpu.r[1] = (-7) & MASK64
    cpu.r[2] = 3

    cpu._execute(("DIV", 3, 1, 2))
    assert cpu.r[3] == scalar_binary("DIV", (-7) & MASK64, 3)
    cpu._execute(("REM", 3, 1, 2))
    assert cpu.r[3] == scalar_binary("REM", (-7) & MASK64, 3)

    cpu._execute(("UDIV", 3, 1, 2))
    assert cpu.r[3] == scalar_binary("UDIV", (-7) & MASK64, 3)
    cpu._execute(("UREM", 3, 1, 2))
    assert cpu.r[3] == scalar_binary("UREM", (-7) & MASK64, 3)


@pytest.mark.parametrize("name", ["DIV", "UDIV", "REM", "UREM"])
def test_divide_by_zero_is_arithmetic_trap(name):
    cpu = CorelessCPU()
    cpu.r[1] = 7
    cpu.r[2] = 0
    with pytest.raises(CorelessTrap) as exc:
        cpu._execute((name, 3, 1, 2))
    assert exc.value.cause == "arithmetic_fault"


@pytest.mark.parametrize("name", ["SHL", "SHR", "SAR", "ROL", "ROR"])
def test_variable_shifts_use_only_low_six_count_bits(name):
    cpu = CorelessCPU()
    cpu.r[1] = 1
    cpu.r[2] = 64
    cpu._execute((name, 3, 1, 2))
    if name in ("SHL", "ROL"):
        assert cpu.r[3] == 1
    else:
        assert cpu.r[3] == 1

    cpu.r[1] = 1 << 63
    cpu.r[2] = 64 + 1
    cpu._execute((name, 3, 1, 2))
    if name == "SHL":
        assert cpu.r[3] == 0
    elif name == "SHR":
        assert cpu.r[3] == 1 << 62
    elif name == "SAR":
        assert cpu.r[3] == 0xC000000000000000
    elif name == "ROL":
        assert cpu.r[3] == 1
    else:
        assert cpu.r[3] == 1 << 62


def test_signed_and_unsigned_comparisons_are_distinct():
    cpu = CorelessCPU()
    cpu.r[1] = MASK64
    cpu.r[2] = 1
    cpu._execute(("SLT", 3, 1, 2))
    assert cpu.r[3] == 1
    cpu._execute(("SLTU", 3, 1, 2))
    assert cpu.r[3] == 0
    cpu._execute(("SEQ", 3, 1, 2))
    assert cpu.r[3] == 0
    cpu._execute(("SNE", 3, 1, 2))
    assert cpu.r[3] == 1


def test_immediate_integer_operations_mask_results():
    cpu = CorelessCPU()
    cpu.r[1] = MASK64
    cpu._execute(("ADDI", 2, 1, 1))
    assert cpu.r[2] == 0
    cpu._execute(("SUBI", 2, 1, 2))
    assert cpu.r[2] == MASK64 - 2
    cpu._execute(("ANDI", 2, 1, 0xF))
    assert cpu.r[2] == 0xF
    cpu._execute(("ORI", 2, 1, 0x10))
    assert cpu.r[2] == MASK64
    cpu._execute(("XORI", 2, 1, 0xF))
    assert cpu.r[2] == MASK64 - 0xF


def test_load_store_widths_and_signedness():
    cpu = CorelessCPU(memory_size=aligned_memory_size())
    cpu.r[1] = 32
    cpu.r[2] = 0x80FF
    cpu._execute(("ST16", 2, 1, 0))
    cpu._execute(("LD16U", 3, 1, 0))
    assert cpu.r[3] == 0x80FF
    cpu._execute(("LD16", 3, 1, 0))
    assert cpu.r[3] == (-32513) & MASK64

    cpu.r[2] = 0xFF
    cpu._execute(("ST8", 2, 1, 4))
    cpu._execute(("LD8U", 3, 1, 4))
    assert cpu.r[3] == 0xFF
    cpu._execute(("LD8", 3, 1, 4))
    assert cpu.r[3] == MASK64


def test_load_store_64_bit_round_trip():
    cpu = CorelessCPU(memory_size=aligned_memory_size())
    cpu.r[1] = 64
    cpu.r[2] = 0xFEDCBA9876543210
    cpu._execute(("ST64", 2, 1, 0))
    cpu.r[2] = 0
    cpu._execute(("LD64", 2, 1, 0))
    assert cpu.r[2] == 0xFEDCBA9876543210


@pytest.mark.parametrize("size", [2, 4, 8])
def test_misaligned_scalar_access_traps(size):
    cpu = CorelessCPU(memory_size=128)
    cpu.r[1] = 17
    with pytest.raises(CorelessTrap) as exc:
        cpu.load_u(cpu.r[1], size)
    assert exc.value.cause == "alignment_fault"


def test_branch_conditions_and_pc_targeting():
    cpu = CorelessCPU()
    cpu.pc = 0x100
    cpu.r[1] = 5
    cpu.r[2] = 5
    assert cpu._execute(("BEQ", 1, 2, 0x20)) == branch_target("BEQ", cpu.pc, cpu.r[1], cpu.r[2], 0x20)
    assert cpu._execute(("BNE", 1, 2, 0x20)) == branch_target("BNE", cpu.pc, cpu.r[1], cpu.r[2], 0x20)

    cpu.r[2] = 6
    assert cpu._execute(("BLT", 1, 2, 0x30)) == branch_target("BLT", cpu.pc, cpu.r[1], cpu.r[2], 0x30)
    assert cpu._execute(("BGE", 1, 2, 0x30)) == branch_target("BGE", cpu.pc, cpu.r[1], cpu.r[2], 0x30)
    assert cpu._execute(("BLTU", 1, 2, 0x30)) == branch_target("BLTU", cpu.pc, cpu.r[1], cpu.r[2], 0x30)

    cpu.r[1] = MASK64
    cpu.r[2] = 1
    assert cpu._execute(("BLT", 1, 2, 0x30)) == branch_target("BLT", cpu.pc, cpu.r[1], cpu.r[2], 0x30)
    assert cpu._execute(("BLTU", 1, 2, 0x30)) == branch_target("BLTU", cpu.pc, cpu.r[1], cpu.r[2], 0x30)


def test_jumps_and_calls_return_architectural_next_pc():
    cpu = CorelessCPU()
    cpu.pc = 0x200
    cpu._execute(("CALL", 1, 2, 0x40))
    assert cpu.r[1] == 0x204
    assert cpu.pc == 0x200
    assert cpu._execute(("J", 0, 0x80, 0)) == jump_target("J", cpu.pc, 0x80)

    cpu.r[4] = 0x900
    assert cpu._execute(("JR", 0, 4, 0x10)) == jump_target("JR", cpu.pc, cpu.r[4], 0x10)
    cpu.r[1] = 0xABC
    assert cpu._execute(("RET",)) == 0xABC


def test_not_and_neg_wrap_to_64_bits():
    cpu = CorelessCPU()
    cpu.r[1] = 0
    cpu._execute(("NOT", 2, 1))
    assert cpu.r[2] == MASK64
    cpu._execute(("NEG", 2, 1))
    assert cpu.r[2] == 0
    cpu.r[1] = 1
    cpu._execute(("NEG", 2, 1))
    assert cpu.r[2] == MASK64
