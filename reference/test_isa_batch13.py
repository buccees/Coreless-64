"""Thirteenth-wave concrete vector instruction conformance batch."""
import sys
sys.path.insert(0, ".")
import pytest
from core import CorelessCPU, CorelessTrap, USER

def w(et=0, mask_en=False, mask_zero=False, mask_reg=0):
    return (et << 29) | (int(mask_en) << 22) | (int(mask_zero) << 21) | (mask_reg << 16)

def setup(vl=4):
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.write_csr(0x012, vl)
    return cpu

def test_vector_mask_merge_preserves_inactive_destination():
    cpu = setup()
    cpu.vector_mask[1] = 0b0101
    cpu.vector[1][:4] = [1, 2, 3, 4]
    cpu.vector[2][:4] = [10, 20, 30, 40]
    cpu.vector[3][:4] = [100, 100, 100, 100]
    cpu._vector_op(3, 0x00, 3, 1, 2, w(mask_en=True, mask_reg=1))
    assert cpu.vector[3][:4] == [11, 100, 33, 100]

def test_vector_mask_zero_writes_zero_without_memory_access():
    cpu = setup()
    cpu.vector_mask[1] = 0b0101
    cpu.vector[1][:4] = [1, 2, 3, 4]
    cpu.vector[2][:4] = [10, 20, 30, 40]
    cpu.vector[3][:4] = [100, 100, 100, 100]
    cpu._vector_op(3, 0x00, 3, 1, 2, w(mask_en=True, mask_zero=True, mask_reg=1))
    assert cpu.vector[3][:4] == [11, 0, 33, 0]

def test_vector_vzero_zeros_only_active_elements():
    cpu = setup(4)
    cpu.vector[3][:6] = [9, 8, 7, 6, 5, 4]
    cpu._vector_op(3, 0x26, 3, 0, 0, w())
    assert cpu.vector[3][:4] == [0, 0, 0, 0]
    assert cpu.vector[3][4:6] == [5, 4]

def test_vector_vshuffle_uses_per_lane_indices():
    cpu = setup()
    cpu.vector[1][:4] = [10, 20, 30, 40]
    cpu.vector[2][:4] = [3, 0, 2, 1]
    cpu._vector_op(3, 0x22, 3, 1, 2, w())
    assert cpu.vector[3][:4] == [40, 10, 30, 20]

def test_vector_vshuffle_rejects_index_outside_vl():
    cpu = setup()
    cpu.vector[1][:4] = [10, 20, 30, 40]
    cpu.vector[2][:4] = [0, 1, 4, 2]
    with pytest.raises(CorelessTrap):
        cpu._vector_op(3, 0x22, 3, 1, 2, w())

def test_vector_vextract_and_vinsert_use_selected_index():
    cpu = setup()
    cpu.vector[1][:4] = [11, 22, 33, 44]
    cpu.write_reg(2, 2)
    cpu._vector_op(3, 0x24, 3, 1, 2, w())
    assert cpu.read_reg(3) == 33
    cpu.write_reg(4, 99)
    cpu.write_reg(2, 1)
    cpu._vector_op(3, 0x25, 3, 4, 2, w())
    assert cpu.vector[3][1] == 99

def test_vector_vextract_and_vinsert_reject_index_outside_vl():
    cpu = setup()
    cpu.write_reg(2, 4)
    with pytest.raises(CorelessTrap):
        cpu._vector_op(3, 0x24, 3, 1, 2, w())
    with pytest.raises(CorelessTrap):
        cpu._vector_op(3, 0x25, 3, 1, 2, w())

def test_vector_masked_gather_does_not_touch_inactive_faulting_lane():
    cpu = setup()
    cpu.vector_mask[1] = 0b0101
    cpu.write_reg(1, len(cpu.memory) - 1)
    cpu.vector[2][:4] = [0, 1, 2, 3]
    cpu.vector[3][:4] = [7, 7, 7, 7]
    with pytest.raises(CorelessTrap):
        cpu._vector_op(3, 0x20, 3, 1, 2, w(mask_en=True, mask_reg=1))
    assert cpu.vector[3][0] == 7

def test_vector_masked_scatter_does_not_touch_inactive_lane():
    cpu = setup()
    cpu.vector_mask[1] = 0b0101
    cpu.write_reg(1, 0x100)
    cpu.vector[2][:4] = [1, 2, 3, 4]
    cpu.vector[3][:4] = [0x11, 0x22, 0x33, 0x44]
    cpu._vector_op(3, 0x21, 3, 1, 2, w(mask_en=True, mask_reg=1))
    assert cpu.load_u(0x100, 1) == 0x11
    assert cpu.load_u(0x102, 1) == 0x33
    assert cpu.load_u(0x101, 1) == 0
    assert cpu.load_u(0x103, 1) == 0

def test_vector_vbroadcast_respects_vl():
    cpu = setup(3)
    cpu.vector[3][:5] = [9, 9, 9, 9, 9]
    cpu.write_reg(1, 0x1234)
    cpu._vector_op(3, 0x23, 3, 1, 0, w())
    assert cpu.vector[3][:3] == [0x1234, 0x1234, 0x1234]
    assert cpu.vector[3][3:5] == [9, 9]
