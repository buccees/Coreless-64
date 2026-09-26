import sys
sys.path.insert(0, ".")
from core import CorelessCPU, USER, MACHINE

def word(op, rd=0, rs1=0, rs2=0, f=0):
    return (op << 27) | (rd << 22) | (rs1 << 17) | (rs2 << 12) | f

def imm(op, rd, rs1, f, value):
    return (op << 27) | (rd << 22) | (rs1 << 17) | (f << 12) | (value & 0xfff)

def sysword(rd, rs1, f, operand=0):
    return (6 << 27) | (rd << 22) | (rs1 << 17) | ((operand & 0x7ff) << 5) | f

def test_scalar_execution_and_zero_register():
    cpu=CorelessCPU()
    cpu.r[1]=7; cpu.r[2]=5
    cpu.memory[0:4]=word(0,3,1,2,0).to_bytes(4,"little")
    cpu.memory[4:8]=word(0,0,3,0,20).to_bytes(4,"little")
    assert cpu.step()
    assert cpu.r[3]==12 and cpu.pc==4 and cpu.instret==1
    assert cpu.step()
    assert cpu.r[0]==0 and cpu.pc==8

def test_immediate_and_memory():
    cpu=CorelessCPU()
    cpu.r[1]=100; cpu.r[2]=0x1122334455667788
    cpu.memory[0:4]=imm(1,2,1,0,7).to_bytes(4,"little")
    cpu.memory[4:8]=((3<<27)|(2<<22)|(1<<17)|(3<<14)).to_bytes(4,"little")
    cpu.memory[8:12]=((2<<27)|(4<<22)|(1<<17)|(3<<14)).to_bytes(4,"little")
    cpu.step(); assert cpu.r[2]==107
    cpu.step(); assert int.from_bytes(cpu.memory[107:115],"little")==0x1122334455667788
    cpu.step(); assert cpu.r[4]==0x1122334455667788

def test_branch_and_call():
    cpu=CorelessCPU()
    cpu.r[1]=1; cpu.r[2]=1
    cpu.memory[0:4]=word(4,1,2,0,0).to_bytes(4,"little")
    cpu.memory[4:8]=imm(1,3,0,0,9).to_bytes(4,"little")
    cpu.step(); assert cpu.pc==0
    cpu.r[1]=0
    cpu.step(); assert cpu.pc==4 and cpu.r[3]==9

def test_divide_by_zero_is_precise_trap():
    cpu=CorelessCPU()
    cpu.r[1]=9
    cpu.memory[0:4]=word(0,2,1,0,3).to_bytes(4,"little")
    cpu.csrs[0x003]=0x100
    cpu.step()
    assert cpu.csrs[0x005] & ((1<<56)-1) == 0x00E
    assert cpu.csrs[0x004] == 0
    assert cpu.pc == 0x100
    assert cpu.instret == 0

def test_csr_read_write():
    cpu=CorelessCPU()
    cpu.r[1]=0x1234
    cpu.memory[0:4]=sysword(0,1,9,0x001).to_bytes(4,"little")
    cpu.step()
    cpu.memory[4:8]=sysword(2,0,8,0x001).to_bytes(4,"little")
    cpu.step()
    assert cpu.r[2] == 0x1234

def test_privilege_trap():
    cpu=CorelessCPU()
    cpu.privilege=USER
    cpu.csrs[0x003]=0x100
    cpu.memory[0:4]=sysword(0,0,7,0).to_bytes(4,"little")
    cpu.step()
    assert cpu.csrs[0x005] & ((1<<56)-1) == 0x004
    assert cpu.pc == 0x100

def test_mmu_translation_and_permissions():
    cpu=CorelessCPU(memory_size=0x10000)
    # Root is a simple single-level 4 KiB PTE array in this reference model.
    cpu.csrs[0x007]=0x1000
    cpu.csrs[0x009]=1
    # VA page 0 -> PA page 2, R/W/X/U.
    pte=(1)|(1<<1)|(1<<2)|(1<<3)|(1<<4)|(2<<12)
    cpu.memory[0x1000:0x1008]=pte.to_bytes(8,"little")
    cpu.memory[0x2000:0x2004]=imm(1,1,0,0,5).to_bytes(4,"little")
    cpu.step()
    assert cpu.r[1]==5 and cpu.instret==1
