"""Eleventh-wave Coreless-64 atomic/memory-ordering conformance batch."""
import sys
sys.path.insert(0, ".")
from core import CorelessCPU

def word(op, rd=0, rs1=0, rs2=0, f=0):
    return (op << 27) | (rd << 22) | (rs1 << 17) | (rs2 << 12) | f

def run_atomic(cpu, rd, addr_reg, src_reg, funct, desired_reg=0, ordering=0):
    raw = word(7, rd, addr_reg, src_reg, funct) | (desired_reg << 4) | (ordering << 9)
    cpu.memory[cpu.pc:cpu.pc+4] = raw.to_bytes(4, "little")
    cpu.step()

def setup(value=10):
    cpu = CorelessCPU()
    cpu.r[1] = 0x100
    cpu.r[2] = 7
    cpu.r[3] = 20
    cpu.memory[0x100:0x108] = value.to_bytes(8, "little")
    return cpu

def mem(cpu):
    return int.from_bytes(cpu.memory[0x100:0x108], "little")

def test_atomic_swap():
    cpu = setup(10)
    run_atomic(cpu, 4, 1, 2, 0)
    assert cpu.r[4] == 10 and mem(cpu) == 7

def test_atomic_cas_success_uses_desired_register():
    cpu = setup(10)
    run_atomic(cpu, 4, 1, 2, 1, desired_reg=3)
    assert cpu.r[4] == 10 and mem(cpu) == 20

def test_atomic_cas_failure_preserves_memory():
    cpu = setup(10)
    cpu.r[2] = 11
    run_atomic(cpu, 4, 1, 2, 1, desired_reg=3)
    assert cpu.r[4] == 10 and mem(cpu) == 10

def test_atomic_fetch_add_wraps():
    cpu = setup((1 << 64) - 2)
    cpu.r[2] = 5
    run_atomic(cpu, 4, 1, 2, 2)
    assert cpu.r[4] == (1 << 64) - 2 and mem(cpu) == 3

def test_atomic_fetch_sub_wraps():
    cpu = setup(2)
    cpu.r[2] = 5
    run_atomic(cpu, 4, 1, 2, 3)
    assert cpu.r[4] == 2 and mem(cpu) == (1 << 64) - 3

def test_atomic_fetch_logic():
    cpu = setup(0xF0)
    cpu.r[2] = 0x0F
    run_atomic(cpu, 4, 1, 2, 4)
    assert mem(cpu) == 0
    cpu = setup(0xF0)
    run_atomic(cpu, 4, 1, 2, 5)
    assert mem(cpu) == 0xF0
    cpu = setup(0xF0)
    run_atomic(cpu, 4, 1, 2, 6)
    assert mem(cpu) == 0xFF

def test_atomic_signed_min_max():
    cpu = setup((1 << 64) - 5)
    cpu.r[2] = (1 << 64) - 7
    run_atomic(cpu, 4, 1, 2, 7)
    assert mem(cpu) == (1 << 64) - 7
    cpu = setup((1 << 64) - 5)
    cpu.r[2] = (1 << 64) - 7
    run_atomic(cpu, 4, 1, 2, 8)
    assert mem(cpu) == (1 << 64) - 5

def test_atomic_load_link_and_store_conditional_round_trip():
    cpu = setup(33)
    run_atomic(cpu, 4, 1, 2, 9, ordering=1)
    assert cpu.r[4] == 33
    cpu.r[2] = 44
    run_atomic(cpu, 5, 1, 2, 10, ordering=1)
    assert mem(cpu) == 44

def test_atomic_load_link_does_not_modify_memory():
    cpu = setup(55)
    run_atomic(cpu, 4, 1, 2, 9)
    assert cpu.r[4] == 55 and mem(cpu) == 55

def test_atomic_ordering_field_is_accepted():
    for ordering in range(5):
        cpu = setup(1)
        cpu.r[2] = 2
        run_atomic(cpu, 4, 1, 2, 0, ordering=ordering)
        assert mem(cpu) == 2 and cpu.r[4] == 1

def test_atomic_address_fault_is_precise():
    cpu = CorelessCPU()
    cpu.r[1] = len(cpu.memory) - 4
    cpu.r[2] = 9
    cpu.csrs[0x003] = 0x200
    run_atomic(cpu, 4, 1, 2, 0)
    assert cpu.pc == 0x200
    assert cpu.csrs[0x006] == len(cpu.memory) - 4
    assert int.from_bytes(cpu.memory[-8:], "little") == 0
