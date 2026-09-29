"""Eighth-wave Coreless-64 floating-point format conformance batch."""
import sys
import math
sys.path.insert(0, ".")

import pytest

from core import CorelessCPU, CorelessTrap
from isa_expect import fp_encode, fp_decode, fp_word


@pytest.mark.parametrize("element_type", [4, 5, 6, 7])
def test_scalar_fp_formats_round_trip(element_type):
    cpu = CorelessCPU()
    value = 1.5
    cpu.f[1] = fp_encode(value, element_type)
    cpu._scalar_fp_op(10, 3, 1, 2, fp_word(element_type))
    got = fp_decode(cpu.f[3], element_type)
    assert got == pytest.approx(value)


@pytest.mark.parametrize("element_type", [4, 5, 6, 7])
def test_scalar_fp_add_uses_selected_format(element_type):
    cpu = CorelessCPU()
    cpu.f[1] = fp_encode(1.25, element_type)
    cpu.f[2] = fp_encode(0.5, element_type)
    cpu._scalar_fp_op(0, 3, 1, 2, fp_word(element_type))
    assert fp_decode(cpu.f[3], element_type) == pytest.approx(
        fp_decode(fp_encode(1.75, element_type), element_type)
    )


@pytest.mark.parametrize("element_type", [4, 5, 6, 7])
def test_scalar_fp_neg_and_abs_preserve_selected_format(element_type):
    cpu = CorelessCPU()
    cpu.f[1] = fp_encode(-3.25, element_type)
    cpu._scalar_fp_op(10, 3, 1, 2, fp_word(element_type))
    assert fp_decode(cpu.f[3], element_type) == pytest.approx(
        fp_decode(fp_encode(3.25, element_type), element_type)
    )
    cpu._scalar_fp_op(11, 3, 1, 2, fp_word(element_type))
    assert fp_decode(cpu.f[3], element_type) == pytest.approx(
        fp_decode(fp_encode(3.25, element_type), element_type)
    )


def test_scalar_fp_bf16_rounding_tie_to_even():
    cpu = CorelessCPU()
    # 1.0 + 2^-8 is exactly halfway between adjacent BF16 values.
    value = 1.0 + 2.0 ** -8
    cpu.f[1] = fp_encode(value, 5)
    cpu._scalar_fp_op(10, 3, 1, 2, fp_word(5))
    assert cpu.f[3] == fp_encode(value, 5)
    assert fp_decode(cpu.f[3], 5) == 1.0


def test_scalar_fp_fp16_overflow_raises_defined_fp_fault():
    cpu = CorelessCPU()
    cpu.f[1] = fp_encode(60000.0, 4)
    cpu.f[2] = fp_encode(2.0, 4)
    with pytest.raises(CorelessTrap) as exc:
        cpu._scalar_fp_op(2, 3, 1, 2, fp_word(4))
    assert exc.value.cause == "floating_point_fault"


@pytest.mark.parametrize("src_type,dst_type", [
    (4, 6), (4, 7), (5, 6), (5, 7), (6, 4), (6, 5),
    (7, 4), (7, 5), (7, 6),
])
def test_scalar_fp_format_conversion(src_type, dst_type):
    cpu = CorelessCPU()
    value = 1.5
    cpu.f[1] = fp_encode(value, src_type)
    word = fp_word(src_type) | (dst_type << 26)
    cpu._scalar_fp_op(12, 3, 1, 2, word)
    assert fp_decode(cpu.f[3], dst_type) == pytest.approx(
        fp_decode(fp_encode(value, dst_type), dst_type)
    )


@pytest.mark.parametrize("dst_type", [4, 5, 6, 7])
def test_scalar_fp_nan_conversion_preserves_nan(dst_type):
    cpu = CorelessCPU()
    cpu.f[1] = fp_encode(float("nan"), 7)
    word = fp_word(7) | (dst_type << 26)
    cpu._scalar_fp_op(12, 3, 1, 2, word)
    assert math.isnan(fp_decode(cpu.f[3], dst_type))


def test_scalar_fp_invalid_rounding_field_is_rejected_for_all_formats():
    for element_type in [4, 5, 6, 7]:
        cpu = CorelessCPU()
        cpu.f[1] = fp_encode(1.0, element_type)
        cpu.f[2] = fp_encode(2.0, element_type)
        with pytest.raises(CorelessTrap) as exc:
            cpu._scalar_fp_op(0, 3, 1, 2, fp_word(element_type) | (1 << 8))
        assert exc.value.cause == "illegal_instruction"
