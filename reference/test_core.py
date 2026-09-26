import sys
sys.path.insert(0, ".")
from core import CorelessCPU

def word(op, rd=0, rs1=0, rs2=0, f=0):
    return (op << 27) | (rd << 22) | (rs1 << 17) | (rs2 << 12) | f

def imm(op, rd, rs1, f, value):
    return (op << 27) | (rd << 22) | (rs1 << 17) | (f << 12) | (value & 0xfff)

def test_scalar_execution_and_zero_register():
    cpu=CorelessCPU()
    cpu.r[1]=7; cpu.r[2]=5
    cpu.memory[0:4]=word(0,3,1,2,0).to_bytes(4,"little")
    cpu.memory[4:8]=word(0,0,3,0,20).to_bytes(4,"little")  # NEG R0,R3
    assert cpu.step()
    assert cpu.r[3]==12 and cpu.pc==4 and cpu.instret==1
    assert cpu.step()
    assert cpu.r[0]==0 and cpu.pc==8

def test_immediate_and_memory():
    cpu=CorelessCPU()
    cpu.r[1]=100
    cpu.memory[0:4]=imm(1,2,1,0,7).to_bytes(4,"little")
    cpu.memory[4:8]=((2<<27)|(3<<22)|(2<<17)|(3<<14)).to_bytes(4,"little")
    cpu.memory[8:12]=((2<<27)|(4<<22)|(2<<17)|(3<<14)|0).to_bytes(4,"little")
    cpu.memory[100:108]=(0x1122334455667788).to_bytes(8,"little")
    cpu.step(); assert cpu.r[2]==107
    cpu.step(); assert cpu.memory[107:115] == (0).to_bytes(8,"little")
    cpu.step(); assert cpu.r[4]==0

def test_branch_and_call():
    cpu=CorelessCPU()
    cpu.r[1]=1; cpu.r[2]=1
    cpu.memory[0:4]=word(4,1,2,0,0).to_bytes(4,"little")
    cpu.memory[4:8]=imm(1,3,0,0,9).to_bytes(4,"little")
    cpu.step(); assert cpu.pc==0
    cpu.r[1]=0
    cpu.step(); assert cpu.pc==4 and cpu.r[3]==9
