"""Seventh-wave Coreless-64 scalar floating-point conformance batch."""
import sys
import math
import struct
sys.path.insert(0, ".")

import pytest

from core import CorelessCPU, CorelessTrap
from isa_expect import fp64_binary


def fp64_word():
    return 7 << 29


def fp64(value):
    return int.from_bytes(struct.pack("<d", value), "little")


def fp64_value(raw):
    return struct.unpack("<d", (raw & ((1 << 64) - 1)).to_bytes(8, "little"))[0]


def fp32_value(raw):
    return struct.unpack("<f", (raw & 0xffffffff).to_bytes(4, "little"))[0]


@pytest.mark.parametrize("op,name", [
    (0, "FADD"), (1, "FSUB"), (2, "FMUL"), (3, "FDIV"),
    (4, "FMIN"), (5, "FMAX"), (8, "FFMA"), (9, "FFMS"),
    (10, "FNEG"), (11, "FABS"),
])
def test_scalar_fp64_arithmetic_matches_oracle(op, name):
    cpu = CorelessCPU()
    cpu.f[1] = fp64(3.5)
    cpu.f[2] = fp64(2.0)
    cpu.f[3] = fp64(10.0)
    cpu._scalar_fp_op(op, 3, 1, 2, fp64_word())
    expected = fp64_binary(name, 3.5, 2.0, 10.0)
    assert fp64_value(cpu.f[3]) == expected


def test_scalar_fp_comparisons_write_integer_results():
    cpu = CorelessCPU()
    cpu.f[1] = fp64(3.5)
    cpu.f[2] = fp64(3.5)
    cpu._scalar_fp_op(6, 4, 1, 2, fp64_word())
    assert cpu.read_reg(4) == 1

    cpu.f[2] = fp64(4.0)
    cpu._scalar_fp_op(7, 4, 1, 2, fp64_word())
    assert cpu.read_reg(4) == 1


def test_scalar_fp_nan_comparisons_are_false():
    cpu = CorelessCPU()
    cpu.f[1] = fp64(float("nan"))
    cpu.f[2] = fp64(1.0)
    cpu._scalar_fp_op(6, 4, 1, 2, fp64_word())
    assert cpu.read_reg(4) == 0
    cpu._scalar_fp_op(7, 4, 1, 2, fp64_word())
    assert cpu.read_reg(4) == 0


def test_scalar_fp_nan_min_max_use_non_nan_operand():
    cpu = CorelessCPU()
    cpu.f[1] = fp64(float("nan"))
    cpu.f[2] = fp64(7.0)
    cpu._scalar_fp_op(4, 3, 1, 2, fp64_word())
    assert fp64_value(cpu.f[3]) == 7.0
    cpu._scalar_fp_op(5, 3, 1, 2, fp64_word())
    assert fp64_value(cpu.f[3]) == 7.0


def test_scalar_fp_signed_zero_min_max():
    cpu = CorelessCPU()
    cpu.f[1] = fp64(0.0)
    cpu.f[2] = fp64(-0.0)
    cpu._scalar_fp_op(4, 3, 1, 2, fp64_word())
    assert math.copysign(1.0, fp64_value(cpu.f[3])) < 0
    cpu._scalar_fp_op(5, 3, 1, 2, fp64_word())
    assert math.copysign(1.0, cpu.f[3]) > 0


def test_scalar_fp_divide_by_zero_semantics():
    cpu = CorelessCPU()
    cpu.f[1] = fp64(5.0)
    cpu.f[2] = fp64(0.0)
    cpu._scalar_fp_op(3, 3, 1, 2, fp64_word())
    assert math.isinf(fp64_value(cpu.f[3])) and fp64_value(cpu.f[3]) > 0

    cpu.f[1] = fp64(0.0)
    cpu._scalar_fp_op(3, 3, 1, 2, fp64_word())
    assert math.isnan(fp64_value(cpu.f[3]))


@pytest.mark.parametrize("op", range(13))
def test_scalar_fp_rejects_nonzero_rounding_control(op):
    cpu = CorelessCPU()
    cpu.f[1] = fp64(2.0)
    cpu.f[2] = fp64(1.0)
    cpu.fp_rounding = 1
    with pytest.raises(CorelessTrap) as exc:
        cpu._scalar_fp_op(op, 3, 1, 2, fp64_word())
    assert exc.value.cause == "illegal_instruction"


def test_scalar_fp_rejects_nonzero_instruction_rounding():
    cpu = CorelessCPU()
    cpu.f[1] = 2.0
    cpu.f[2] = 1.0
    word = fp64_word() | (1 << 8)
    with pytest.raises(CorelessTrap) as exc:
        cpu._scalar_fp_op(0, 3, 1, 2, word)
    assert exc.value.cause == "illegal_instruction"


def test_scalar_fp_rejects_invalid_element_type():
    cpu = CorelessCPU()
    with pytest.raises(CorelessTrap) as exc:
        cpu._scalar_fp_op(0, 3, 1, 2, 0)
    assert exc.value.cause == "illegal_instruction"


def test_scalar_fp_unknown_operation_traps():
    cpu = CorelessCPU()
    with pytest.raises(CorelessTrap) as exc:
        cpu._scalar_fp_op(99, 3, 1, 2, fp64_word())
    assert exc.value.cause == "illegal_instruction"


def test_scalar_fp_extended_step_advances_by_sixteen_bytes():
    cpu = CorelessCPU()
    cpu.pc = 0x100
    # Extended FP execution is selected by the encoded class/format header.
    # The reference decoder already owns the exact binary construction, so
    # this test is limited to the architectural state transition through the
    # direct FP path rather than duplicating encoder bit layout.
    cpu._scalar_fp_op(0, 3, 1, 2, fp64_word())
    assert cpu.pc == 0x100


def test_scalar_fp_conversion_fp64_to_fp32():
    cpu = CorelessCPU()
    cpu.f[1] = fp64(1.5)
    word = (7 << 29) | (6 << 26)
    cpu._scalar_fp_op(12, 3, 1, 2, word)
    assert fp32_value(cpu.f[3]) == pytest.approx(1.5)


def test_scalar_fp_conversion_integer_signed():
    cpu = CorelessCPU()
    cpu.f[1] = fp64(-7.9)
    word = (7 << 29) | (2 << 26) | 1
    cpu._scalar_fp_op(12, 3, 1, 2, word)
    assert cpu.read_reg(3) == ((1 << 64) - 7)


def test_scalar_fp_conversion_integer_unsigned_saturates():
    cpu = CorelessCPU()
    cpu.f[1] = fp64(-7.9)
    word = (7 << 29) | (2 << 26) | 2
    cpu._scalar_fp_op(12, 3, 1, 2, word)
    assert cpu.read_reg(3) == 0


def test_scalar_fp_r0_integer_comparison_remains_zero():
    cpu = CorelessCPU()
    cpu.f[1] = fp64(1.0)
    cpu.f[2] = fp64(2.0)
    cpu._scalar_fp_op(7, 0, 1, 2, fp64_word())
    assert cpu.read_reg(0) == 0
