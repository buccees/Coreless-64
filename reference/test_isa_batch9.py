"""Ninth-wave Coreless-64 vector conformance batch."""
import sys, struct, math
sys.path.insert(0, ".")
import pytest
from core import CorelessCPU, CorelessTrap
from isa_expect import vector_int_binary, vector_fp_binary, vector_reduce, fp_encode, fp_decode

def cpu_vl(vl=8):
    cpu = CorelessCPU()
    cpu.vector_vl = vl
    return cpu

def et_word(et, mask_en=False, mask_zero=False, mask_reg=0):
    return (et << 29) | (int(mask_en) << 22) | (int(mask_zero) << 21) | (mask_reg << 16)

@pytest.mark.parametrize("op,name", [
    (0x00,"VADD"), (0x01,"VSUB"), (0x02,"VMUL"),
    (0x06,"VAND"), (0x07,"VOR"), (0x08,"VXOR"),
    (0x0A,"VSHL"), (0x0B,"VSHR"), (0x0C,"VSAR"),
    (0x0F,"VSEQ"), (0x10,"VSLT"), (0x11,"VSLTU"),
])
def test_vector_integer_ops_match_oracle(op, name):
    cpu = cpu_vl()
    cpu.vector[1][:8] = [0x80, 7, 0x55, 3, 0xF0, 2, 0x81, 9]
    cpu.vector[2][:8] = [1, 3, 2, 5, 0x0F, 7, 2, 1]
    cpu._vector_op(1, op, 3, 1, 2, et_word(0))
    expected = [vector_int_binary(name, a, b, 8) for a,b in zip(cpu.vector[1][:8], cpu.vector[2][:8])]
    assert cpu.vector[3][:8] == expected

def test_vector_mask_merge_and_zeroing():
    cpu = cpu_vl(4)
    cpu.vector[1][:4] = [1,2,3,4]
    cpu.vector[2][:4] = [10,20,30,40]
    cpu.vector[3][:4] = [99,99,99,99]
    cpu.vector_mask[0] = 0b0101
    cpu._vector_op(1, 0x00, 3, 1, 2, et_word(0, True, False))
    assert cpu.vector[3][:4] == [11,99,33,99]
    cpu.vector[3][:4] = [99,99,99,99]
    cpu._vector_op(1, 0x00, 3, 1, 2, et_word(0, True, True))
    assert cpu.vector[3][:4] == [11,0,33,0]

@pytest.mark.parametrize("op,name", [(0x18,"VREDSUM"),(0x1B,"VREDAND"),(0x1C,"VREDOR"),(0x1D,"VREDXOR")])
def test_vector_integer_reductions_match_oracle(op, name):
    cpu = cpu_vl(5)
    values = [1,2,4,8,16]
    cpu.vector[1][:5] = values
    cpu._vector_op(1, op, 3, 1, 2, et_word(0))
    assert cpu.read_reg(3) == vector_reduce(name, values, 8)

def test_vector_reduction_mask_excludes_inactive_lanes():
    cpu = cpu_vl(5)
    cpu.vector[1][:5] = [1,2,4,8,16]
    cpu.vector_mask[0] = 0b10101
    cpu._vector_op(1, 0x18, 3, 1, 2, et_word(0, True))
    assert cpu.read_reg(3) == 21

@pytest.mark.parametrize("op,name", [(0x00,"VFADD"),(0x01,"VFSUB"),(0x02,"VFMUL"),(0x04,"VFMIN"),(0x05,"VFMAX"),(0x13,"VFFMA")])
def test_vector_fp64_ops_match_oracle(op, name):
    cpu = cpu_vl(4)
    cpu.vector[1][:4] = [fp_encode(3.0,7)] * 4
    cpu.vector[2][:4] = [fp_encode(2.0,7)] * 4
    cpu.vector[3][:4] = [fp_encode(4.0,7)] * 4
    cpu._vector_op(1, op, 3, 1, 2, et_word(7))
    expected = vector_fp_binary(name, 3.0, 2.0, 4.0)
    assert all(fp_decode(x,7) == expected for x in cpu.vector[3][:4])

def test_vector_fp_formats_and_nan_minmax():
    for et in (4,5,6,7):
        cpu = cpu_vl(2)
        cpu.vector[1][:2] = [fp_encode(float("nan"),et), fp_encode(1.0,et)]
        cpu.vector[2][:2] = [fp_encode(7.0,et), fp_encode(float("nan"),et)]
        cpu._vector_op(1, 0x04, 3, 1, 2, et_word(et))
        assert fp_decode(cpu.vector[3][0],et) == 7.0
        assert fp_decode(cpu.vector[3][1],et) == 1.0

def test_vector_strided_load_store():
    cpu = cpu_vl(4)
    cpu.write_reg(1, 0x100)
    cpu.write_reg(2, 4)
    for i,v in enumerate((11,22,33,44)):
        cpu.store_u(0x100 + i*4, 4, v)
    cpu._vector_op(1, 0x1E, 3, 1, 2, et_word(2))
    assert cpu.vector[3][:4] == [11,22,33,44]
    cpu.vector[3][:4] = [55,66,77,88]
    cpu._vector_op(1, 0x1F, 3, 1, 2, et_word(2))
    assert [cpu.load_u(0x100+i*4,4) for i in range(4)] == [55,66,77,88]

def test_vector_indexed_load_respects_mask_without_memory_access():
    cpu = cpu_vl(4)
    cpu.write_reg(1, 0x100)
    cpu.vector[2][:4] = [0,4,8,0xFFFFFFFF]
    cpu.store_u(0x100, 4, 0)
    cpu.store_u(0x108, 4, 8)
    cpu.vector_mask[0] = 0b0101
    cpu._vector_op(1, 0x20, 3, 1, 2, et_word(2, True))
    assert cpu.vector[3][:4] == [0,0,8,0]

def test_vector_move_and_select():
    cpu = cpu_vl(4)
    cpu.vector[1][:4] = [1,2,3,4]
    cpu.vector[2][:4] = [10,20,30,40]
    cpu.vector_mask[0] = 0b0101
    cpu._vector_op(1, 0x12, 3, 1, 2, et_word(0))
    assert cpu.vector[3][:4] == [1,20,3,40]
    cpu.write_reg(1, 123)
    cpu._vector_op(1, 0x23, 3, 1, 2, et_word(0))
    assert cpu.vector[3][:4] == [123,123,123,123]
