"""Twelfth-wave Coreless-64 vector-control and restart conformance batch."""
import sys
sys.path.insert(0, ".")
import pytest
from core import CorelessCPU, CorelessTrap, USER

def et_word(et=0, mask_en=False, mask_zero=False, mask_reg=0):
    return (et << 29) | (int(mask_en) << 22) | (int(mask_zero) << 21) | (mask_reg << 16)

def test_vector_control_csrs_round_trip_architectural_state():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.write_csr(0x011, 3)
    cpu.write_csr(0x012, 8)
    cpu.write_csr(0x013, 0x1234)
    cpu.write_csr(0x014, 0x5)
    assert cpu.read_csr(0x011) == 3
    assert cpu.read_csr(0x012) == 8
    assert cpu.read_csr(0x013) == 0x1234
    assert cpu.read_csr(0x014) == 0x5
    assert cpu.vector_vstart == 3
    assert cpu.vector_vl == 8
    assert cpu.vector_vtype == 0x1234

def test_vector_vl_controls_active_elements():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.write_csr(0x012, 4)
    cpu.vector[1][:8] = list(range(1, 9))
    cpu.vector[2][:8] = [10] * 8
    cpu._vector_op(3, 0x00, 3, 1, 2, et_word(0))
    assert cpu.vector[3][:4] == [11, 12, 13, 14]
    assert cpu.vector[3][4:8] == [0, 0, 0, 0]

def test_vector_vstart_restarts_at_selected_lane():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.write_csr(0x012, 6)
    cpu.write_csr(0x011, 3)
    cpu.vector[1][:6] = [1, 2, 3, 4, 5, 6]
    cpu.vector[2][:6] = [10] * 6
    cpu.vector[3][:6] = [99] * 6
    cpu._vector_op(3, 0x00, 3, 1, 2, et_word(0))
    assert cpu.vector[3][:3] == [99, 99, 99]
    assert cpu.vector[3][3:6] == [14, 15, 16]
    assert cpu.vector_vstart == 0
    assert cpu.read_csr(0x011) == 0

def test_vector_vstart_is_preserved_when_an_active_lane_faults():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.write_csr(0x012, 4)
    cpu.vector[1][:4] = [0x100, 0x104, 0x108, 0xFFFFFFFFFFFFFFFF]
    cpu.write_reg(1, 0)
    with pytest.raises(CorelessTrap):
        cpu._vector_op(3, 0x20, 3, 1, 1, et_word(2))
    assert cpu.vector_vstart == 3

def test_vector_control_state_is_restored_by_explicit_csr_write():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.write_csr(0x012, 5)
    cpu.write_csr(0x011, 2)
    assert cpu.vector_vl == 5
    assert cpu.vector_vstart == 2
    cpu.write_csr(0x012, 7)
    cpu.write_csr(0x011, 0)
    assert cpu.read_csr(0x012) == 7
    assert cpu.read_csr(0x011) == 0
