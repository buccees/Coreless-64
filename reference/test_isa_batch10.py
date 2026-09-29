"""Tenth-wave Coreless-64 matrix/AI conformance batch."""
import sys
sys.path.insert(0, ".")

import pytest

from core import CorelessCPU, CorelessTrap
from isa_expect import (
    MATRIX_TYPE_BITS,
    matrix_clamp,
    matrix_convert,
    matrix_elementwise,
    matrix_matmul,
    matrix_reduce,
)


def cpu_matrix():
    return CorelessCPU()


def w1(it=0, at=2, shape=0, signed=False):
    return (it << 29) | (at << 26) | (shape << 23) | (int(signed) << 22)


def put_tile(cpu, tile, values):
    for i, row in enumerate(values):
        for j, value in enumerate(row):
            cpu.matrix[tile][i][j] = value


def get_tile(cpu, tile, m=2, n=2):
    return [row[:n] for row in cpu.matrix[tile][:m]]


def test_mmul_matches_independent_oracle():
    cpu = cpu_matrix()
    a = [[1, 2], [3, 4]]
    b = [[5, 6], [7, 8]]
    put_tile(cpu, 1, a)
    put_tile(cpu, 2, b)

    cpu._matrix_op(0x00, 3, 1, 2, w1(0, 2, 0), 0, 0)

    assert get_tile(cpu, 3) == matrix_matmul(
        a, b, 2, 2, 2, 8, 32
    )


def test_mmac_accumulates_into_destination():
    cpu = cpu_matrix()
    a = [[1, 2], [3, 4]]
    b = [[5, 6], [7, 8]]
    prior = [[10, 20], [30, 40]]
    put_tile(cpu, 1, a)
    put_tile(cpu, 2, b)
    put_tile(cpu, 3, prior)

    cpu._matrix_op(0x01, 3, 1, 2, w1(0, 2, 0), 0, 0)

    assert get_tile(cpu, 3) == matrix_matmul(
        a, b, 2, 2, 2, 8, 32, acc=prior
    )


def test_madd_msub_match_oracle():
    cpu = cpu_matrix()
    a = [[200, 3], [4, 5]]
    b = [[100, 8], [2, 9]]
    put_tile(cpu, 1, a)
    put_tile(cpu, 2, b)

    cpu._matrix_op(0x04, 3, 1, 2, w1(0, 0, 0), 0, 0)
    assert get_tile(cpu, 3) == matrix_elementwise("MADD", a, b, 2, 2, 8, 8)

    cpu._matrix_op(0x05, 3, 1, 2, w1(0, 0, 0), 0, 0)
    assert get_tile(cpu, 3) == matrix_elementwise("MSUB", a, b, 2, 2, 8, 8)


def test_signed_matrix_multiply_decodes_twos_complement():
    cpu = cpu_matrix()
    a = [[0xFF, 2], [3, 4]]
    b = [[2, 1], [1, 2]]
    put_tile(cpu, 1, a)
    put_tile(cpu, 2, b)

    cpu._matrix_op(0x00, 3, 1, 2, w1(0, 2, 0, True), 0, 0)

    assert get_tile(cpu, 3) == matrix_matmul(
        a, b, 2, 2, 2, 8, 32, signed=True
    )


def test_matrix_conversion_and_clamp():
    cpu = cpu_matrix()
    values = [[0xFF, 2], [127, 0x80]]
    put_tile(cpu, 1, values)

    cpu._matrix_op(0x08, 3, 1, 2, w1(0, 1, 0, True), 0, 0)
    assert get_tile(cpu, 3) == matrix_convert(values, 2, 2, 8, 16, signed=True)

    cpu._matrix_op(0x0E, 3, 1, 2, w1(1, 1, 0, True), 0, (5 << 16) | 0xFFFB)
    assert get_tile(cpu, 3) == matrix_clamp(
        values, 2, 2, 16, 16, -5, 5, signed=True
    )


def test_matrix_reduce_writes_scalar_destination():
    cpu = cpu_matrix()
    values = [[1, 2], [3, 4]]
    put_tile(cpu, 1, values)

    cpu._matrix_op(0x0D, 3, 1, 2, w1(0, 0, 0), 0, 0)

    assert cpu.read_reg(3) == matrix_reduce(values, 2, 2, 8)


def test_matrix_zero_and_broadcast():
    cpu = cpu_matrix()
    put_tile(cpu, 3, [[9, 9], [9, 9]])

    cpu._matrix_op(0x0B, 3, 1, 2, w1(), 0, 0)
    assert get_tile(cpu, 3) == [[0, 0], [0, 0]]

    cpu.write_reg(1, 0x1234)
    cpu._matrix_op(0x0C, 3, 1, 2, w1(), 0, 0)
    assert get_tile(cpu, 3) == [[0x1234, 0x1234], [0x1234, 0x1234]]


def test_matrix_transpose():
    cpu = cpu_matrix()
    values = [[1, 2], [3, 4]]
    put_tile(cpu, 1, values)

    cpu._matrix_op(0x07, 3, 1, 2, w1(), 0, 0)

    assert get_tile(cpu, 3) == [[1, 3], [2, 4]]


def test_matrix_mmuladd_uses_descriptor_tile():
    cpu = cpu_matrix()
    a = [[1, 2], [3, 4]]
    b = [[5, 6], [7, 8]]
    add = [[9, 10], [11, 12]]
    put_tile(cpu, 1, a)
    put_tile(cpu, 2, b)
    put_tile(cpu, 4, add)

    cpu._matrix_op(0x06, 3, 1, 2, w1(0, 2, 0), 4, 0)

    assert get_tile(cpu, 3) == matrix_matmul(
        a, b, 2, 2, 2, 8, 32, acc=add
    )


def test_matrix_quantized_mac_applies_zero_points_shift_and_clamp():
    cpu = cpu_matrix()
    put_tile(cpu, 1, [[3, 4], [5, 6]])
    put_tile(cpu, 2, [[2, 1], [4, 3]])
    # za=1, zb=1, zo=2, shift=1; clamp [-2, 20]
    w2 = 1 | (1 << 8) | (2 << 16) | (1 << 24)
    w3 = ((20 & 0xFFFF) << 16) | ((-2) & 0xFFFF)

    cpu._matrix_op(0x03, 3, 1, 2, w1(0, 2, 0), w2, w3)

    expected = [[7, 5], [11, 7]]
    assert get_tile(cpu, 3) == expected


def test_matrix_load_store_respects_descriptor_strides():
    cpu = cpu_matrix()
    base = 0x200
    cpu.write_reg(1, base)
    cpu.store_u(base + 0, 4, 11)
    cpu.store_u(base + 4, 4, 22)
    cpu.store_u(base + 16, 4, 33)
    cpu.store_u(base + 20, 4, 44)

    # 32-bit elements, row stride 16, column stride 4.
    w2 = 16 | (4 << 16)
    cpu._matrix_op(0x09, 3, 1, 2, w1(2, 2, 0), w2, 0)
    assert get_tile(cpu, 3) == [[11, 22], [33, 44]]

    put_tile(cpu, 3, [[55, 66], [77, 88]])
    cpu._matrix_op(0x0A, 3, 1, 2, w1(2, 2, 0), w2, 0)
    assert [cpu.load_u(base + o, 4) for o in (0, 4, 16, 20)] == [55, 66, 77, 88]


def test_matrix_store_preflights_before_mutating_memory():
    cpu = cpu_matrix()
    cpu.write_reg(1, 0xFFC)
    put_tile(cpu, 3, [[1, 2], [3, 4]])

    with pytest.raises(CorelessTrap) as exc:
        cpu._matrix_op(0x0A, 3, 1, 2, w1(2, 2, 0), 16 | (4 << 16), 0)

    assert exc.value.cause == "data_access_fault"
    assert cpu.load_u(0xFFC, 4) == 0


@pytest.mark.parametrize("op", [0x00, 0x01, 0x02, 0x03, 0x04, 0x08, 0x0D, 0x0E])
def test_invalid_matrix_shape_traps(op):
    cpu = cpu_matrix()
    with pytest.raises(CorelessTrap) as exc:
        cpu._matrix_op(op, 3, 1, 2, w1(0, 2, 7), 0, 0)
    assert exc.value.cause in ("matrix_ai_fault", "capability_resource_fault")


def test_mmdot_rejects_floating_point_types():
    cpu = cpu_matrix()
    with pytest.raises(CorelessTrap) as exc:
        cpu._matrix_op(0x02, 3, 1, 2, w1(4, 4, 0), 0, 0)
    assert exc.value.cause == "matrix_ai_fault"


def test_matrix_qmac_rejects_unsupported_types():
    cpu = cpu_matrix()
    with pytest.raises(CorelessTrap) as exc:
        cpu._matrix_op(0x03, 3, 1, 2, w1(4, 2, 0), 0, 0)
    assert exc.value.cause == "matrix_ai_fault"


def test_matrix_invalid_clamp_bounds_trap():
    cpu = cpu_matrix()
    with pytest.raises(CorelessTrap) as exc:
        cpu._matrix_op(0x0E, 3, 1, 2, w1(0, 1, 0), 0, (10 << 16) | 20)
    assert exc.value.cause == "matrix_ai_fault"
