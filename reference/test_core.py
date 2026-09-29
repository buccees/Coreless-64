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
    cpu.r[1]=104; cpu.r[2]=0x1122334455667788
    cpu.memory[0:4]=imm(1,3,1,0,7).to_bytes(4,"little")
    cpu.memory[4:8]=((3<<27)|(2<<22)|(1<<17)|(3<<14)).to_bytes(4,"little")
    cpu.memory[8:12]=((2<<27)|(4<<22)|(1<<17)|(3<<14)).to_bytes(4,"little")
    cpu.step(); assert cpu.r[3]==111
    cpu.step(); assert int.from_bytes(cpu.memory[104:112],"little")==0x1122334455667788
    cpu.step(); assert cpu.r[4]==0x1122334455667788

def test_branch_and_call():
    cpu=CorelessCPU()
    cpu.r[1]=1; cpu.r[2]=1
    cpu.memory[0:4]=word(4,1,2,0,0).to_bytes(4,"little")
    cpu.memory[4:8]=imm(1,3,0,0,9).to_bytes(4,"little")
    cpu.step(); assert cpu.pc==0
    cpu.r[1]=0
    cpu.step(); assert cpu.pc==4 and cpu.r[3]==0
    cpu.step(); assert cpu.pc==8 and cpu.r[3]==9

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


def ext128(cls, op, rd=0, rs1=0, rs2=0, w1=0, w2=0, w3=0):
    header = (0x1E << 27) | (cls << 23) | (op << 17) | (rd << 12) | (rs1 << 7) | (rs2 << 2) | 2
    return b"".join(x.to_bytes(4, "little") for x in (header, w1, w2, w3))

def test_atomic_swap_and_cas():
    cpu=CorelessCPU()
    cpu.r[1]=0x100; cpu.r[2]=7; cpu.r[3]=9
    cpu.memory[0x100:0x108]=(5).to_bytes(8,"little")
    # SWAP R4,[R1],R2
    cpu.memory[0:4]=word(7,4,1,2,0).to_bytes(4,"little")
    cpu.step()
    assert cpu.r[4]==5 and int.from_bytes(cpu.memory[0x100:0x108],"little")==7
    # CAS R5,[R1], expected R2=7, desired R3=9; desired register is bits 11:7.
    cas=(7<<27)|(5<<22)|(1<<17)|(2<<12)|(3<<4)|1
    cpu.memory[4:8]=cas.to_bytes(4,"little")
    cpu.step()
    assert cpu.r[5]==7 and int.from_bytes(cpu.memory[0x100:0x108],"little")==9

def test_vector_vadd_and_mask():
    cpu=CorelessCPU()
    cpu.vector_vl=4
    cpu.vector[1][:4]=[1,2,3,4]
    cpu.vector[2][:4]=[10,20,30,40]
    cpu.memory[0:16]=ext128(3,0x00,3,1,2,w1=(0<<29))
    cpu.step()
    assert cpu.vector[3][:4]==[11,22,33,44] and cpu.pc==16
    cpu.vector_mask[0]=0b0101
    cpu.vector[4][:4]=[1,1,1,1]
    cpu.vector[1][:4]=[1,1,1,1]
    cpu.vector[2][:4]=[2,2,2,2]
    cpu.memory[16:32]=ext128(3,0x00,4,1,2,w1=(0<<29)|(1<<22))
    cpu.step()
    assert cpu.vector[4][:4]==[3,1,3,1]

def test_vector_vzero():
    cpu=CorelessCPU()
    cpu.vector_vl=4
    cpu.vector[5][:4]=[9,9,9,9]
    cpu.memory[0:16]=ext128(3,0x26,5,0,0,w1=0)
    cpu.step()
    assert cpu.vector[5][:4]==[0,0,0,0]

def test_matrix_mmul():
    cpu=CorelessCPU()
    cpu.matrix_shape=(2,2,2)
    cpu.matrix[1][0][:2]=[1,2]; cpu.matrix[1][1][:2]=[3,4]
    cpu.matrix[2][0][:2]=[5,6]; cpu.matrix[2][1][:2]=[7,8]
    cpu.memory[0:16]=ext128(4,0x00,3,1,2,w1=(0<<23))
    cpu.step()
    assert cpu.matrix[3][0][:2]==[19,22]
    assert cpu.matrix[3][1][:2]==[43,50]

def test_matrix_mmac():
    cpu=CorelessCPU()
    cpu.matrix[3][0][:2]=[1,1]; cpu.matrix[3][1][:2]=[1,1]
    cpu.matrix[1][0][:2]=[1,0]; cpu.matrix[1][1][:2]=[0,1]
    cpu.matrix[2][0][:2]=[2,3]; cpu.matrix[2][1][:2]=[4,5]
    cpu.memory[0:16]=ext128(4,0x01,3,1,2,w1=(0<<23))
    cpu.step()
    assert cpu.matrix[3][0][:2]==[3,4]
    assert cpu.matrix[3][1][:2]==[5,6]


def test_matrix_extended_arithmetic_and_conversion():
    cpu=CorelessCPU()
    cpu.matrix_shape=(2,2,2)
    cpu.matrix[1][0][:2]=[1,2]; cpu.matrix[1][1][:2]=[3,4]
    cpu.matrix[2][0][:2]=[5,6]; cpu.matrix[2][1][:2]=[7,8]
    cpu.memory[0:16]=ext128(4,0x04,3,1,2,w1=0)
    cpu.step(); assert cpu.matrix[3][0][:2]==[6,8] and cpu.matrix[3][1][:2]==[10,12]
    cpu.memory[16:32]=ext128(4,0x05,4,2,1,w1=0)
    cpu.step(); assert cpu.matrix[4][0][:2]==[4,4] and cpu.matrix[4][1][:2]==[4,4]
    cpu.memory[32:48]=ext128(4,0x07,5,1,0,w1=0)
    cpu.step(); assert cpu.matrix[5][0][:2]==[1,3] and cpu.matrix[5][1][:2]==[2,4]
    cpu.memory[48:64]=ext128(4,0x0B,5,0,0,w1=0)
    cpu.step(); assert cpu.matrix[5][0][:2]==[0,0] and cpu.matrix[5][1][:2]==[0,0]
    cpu.r[6]=9
    cpu.memory[64:80]=ext128(4,0x0C,6,6,0,w1=0)
    cpu.step(); assert cpu.matrix[6][0][:2]==[9,9] and cpu.matrix[6][1][:2]==[9,9]
    cpu.memory[80:96]=ext128(4,0x0D,7,6,0,w1=0)
    cpu.step(); assert cpu.r[7]==36
    cpu.memory[96:112]=ext128(4,0x0E,6,6,0,w1=0,w3=(2 & 0xFFFF)|((7 & 0xFFFF)<<16))
    cpu.step(); assert cpu.matrix[6][0][:2]==[7,7] and cpu.matrix[6][1][:2]==[7,7]

def test_matrix_memory_and_mmuladd():
    cpu=CorelessCPU(memory_size=0x2000)
    cpu.matrix_shape=(2,2,2)
    cpu.r[1]=0x100
    cpu.memory[0x100:0x108]=bytes([1,2,3,4,5,6,7,8])
    cpu.memory[0:16]=ext128(4,0x09,1,1,0,w1=0,w2=2|(1<<16))
    cpu.step(); assert cpu.matrix[1][0][:2]==[1,2] and cpu.matrix[1][1][:2]==[3,4]
    cpu.matrix[2][0][:2]=[5,6]; cpu.matrix[2][1][:2]=[7,8]
    cpu.matrix[3][0][:2]=[1,1]; cpu.matrix[3][1][:2]=[1,1]
    cpu.memory[16:32]=ext128(4,0x06,3,1,2,w1=0,w2=3)
    cpu.step(); assert cpu.matrix[3][0][:2]==[20,23] and cpu.matrix[3][1][:2]==[44,51]
    cpu.memory[32:48]=ext128(4,0x0A,3,1,0,w1=0,w2=2|(4<<16))
    cpu.step(); assert bytes(cpu.memory[0x100:0x108])==bytes([20,2,44,4,23,6,51,8])

def test_matrix_mmdot_and_type_conversion():
    cpu=CorelessCPU()
    cpu.matrix_shape=(2,2,2)
    cpu.matrix[1][0][:2]=[1,2]; cpu.matrix[1][1][:2]=[3,4]
    cpu.matrix[2][0][:2]=[5,6]; cpu.matrix[2][1][:2]=[7,8]
    cpu.memory[0:16]=ext128(4,0x02,3,1,2,w1=0)
    cpu.step()
    assert cpu.matrix[3][0][:2]==[19,22] and cpu.matrix[3][1][:2]==[43,50]
    cpu.memory[16:32]=ext128(4,0x08,4,3,0,w1=(0<<29)|(1<<26))
    cpu.step()
    assert cpu.matrix[4][0][:2]==[19,22] and cpu.matrix[4][1][:2]==[43,50]


def test_matrix_quantized_mac_rejects_unsupported_types():
    cpu=CorelessCPU()
    cpu.memory[0:16]=ext128(4,0x03,3,1,2,w1=(6<<29)|(2<<26))
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x011

def test_matrix_quantized_mac():
    cpu=CorelessCPU()
    cpu.matrix_shape=(2,2,2)
    cpu.matrix[1][0][:2]=[3,4]; cpu.matrix[1][1][:2]=[5,6]
    cpu.matrix[2][0][:2]=[2,1]; cpu.matrix[2][1][:2]=[4,3]
    w2=(1<<24)
    w3=(0 & 0xFFFF)|((127 & 0xFFFF)<<16)
    cpu.memory[0:16]=ext128(4,0x03,3,1,2,w1=0,w2=w2,w3=w3)
    cpu.step(); assert cpu.matrix[3][0][:2]==[11,7] and cpu.matrix[3][1][:2]==[17,11]


def test_vector_floating_point_baseline():
    import math, struct
    cpu=CorelessCPU()
    cpu.vector_vl=2
    def f32(x):
        return int.from_bytes(struct.pack("<f", x), "little")
    def bf16(x):
        raw=int.from_bytes(struct.pack("<f", x), "little")
        return (raw + 0x8000) >> 16
    cpu.vector[1][:2]=[f32(1.5), f32(-2.0)]
    cpu.vector[2][:2]=[f32(2.0), f32(0.5)]
    cpu.memory[0:16]=ext128(3,0x00,3,1,2,w1=6<<29)
    cpu.step()
    assert [struct.unpack("<f", x.to_bytes(4,"little"))[0] for x in cpu.vector[3][:2]] == [3.5,-1.5]
    cpu.memory[16:32]=ext128(3,0x13,4,1,2,w1=6<<29)
    cpu.vector[4][:2]=[f32(1.0), f32(1.0)]
    cpu.step()
    assert [struct.unpack("<f", x.to_bytes(4,"little"))[0] for x in cpu.vector[4][:2]] == [4.0,0.0]
    cpu.memory[32:48]=ext128(3,0x10,5,1,2,w1=6<<29)
    cpu.step()
    assert cpu.vector[5][:2] == [1,1]
    cpu.vector[1][:2]=[0x7FC00000, f32(1.0)]
    cpu.vector[2][:2]=[f32(2.0), f32(2.0)]
    cpu.memory[48:64]=ext128(3,0x0F,5,1,2,w1=6<<29)
    cpu.step()
    assert cpu.vector[5][:2] == [0,0]
    cpu.vector[1][:2]=[bf16(1.5), bf16(-2.0)]
    cpu.vector[2][:2]=[bf16(0.5), bf16(1.0)]
    cpu.memory[64:80]=ext128(3,0x00,6,1,2,w1=5<<29)
    cpu.step()
    assert cpu.vector[6][:2] == [bf16(2.0), bf16(-1.0)]

def test_vector_floating_point_edge_cases_and_masking():
    import struct, math
    cpu=CorelessCPU(); cpu.vector_vl=2
    def f32(x): return int.from_bytes(struct.pack("<f", x), "little")
    def u32(x): return struct.unpack("<f", x.to_bytes(4,"little"))[0]
    nan=f32(float("nan")); inf=f32(float("inf")); ninf=f32(float("-inf"))
    cpu.vector[1][:2]=[nan, f32(2.0)]
    cpu.vector[2][:2]=[f32(1.0), inf]
    cpu.memory[0:16]=ext128(3,0x00,3,1,2,w1=(6<<29))
    cpu.step()
    assert math.isnan(u32(cpu.vector[3][0])) and math.isinf(u32(cpu.vector[3][1]))
    cpu.vector[1][:2]=[f32(-0.0), f32(1.0)]
    cpu.vector[2][:2]=[f32(0.0), f32(2.0)]
    cpu.memory[16:32]=ext128(3,0x04,4,1,2,w1=(6<<29))
    cpu.step()
    assert math.copysign(1.0,u32(cpu.vector[4][0])) < 0
    cpu.vector_mask[1]=0b01
    cpu.vector[1][:2]=[f32(3.0), f32(99.0)]
    cpu.vector[2][:2]=[f32(4.0), f32(4.0)]
    cpu.memory[32:48]=ext128(3,0x00,5,1,2,w1=(6<<29)|(1<<22)|(1<<16))
    cpu.step()
    assert u32(cpu.vector[5][0]) == 7.0 and cpu.vector[5][1] == 0

def test_vector_floating_point_reductions():
    import struct, math
    cpu=CorelessCPU()
    cpu.vector_vl=3
    def f32(x): return int.from_bytes(struct.pack("<f", x), "little")
    def u32(x): return struct.unpack("<f", x.to_bytes(4,"little"))[0]
    cpu.vector[1][:3]=[f32(1.5),f32(2.0),f32(-0.5)]
    # FP32 VREDUCE_ADD
    cpu.memory[0:16]=ext128(3,0x18,2,1,0,w1=(6<<29))
    cpu.step()
    assert abs(u32(cpu.vector[2][0])-3.0) < 1e-6
    # FP32 VREDUCE_MIN/MAX
    cpu.vector[1][:3]=[f32(1.5),f32(-2.0),f32(0.5)]
    cpu.memory[16:32]=ext128(3,0x19,3,1,0,w1=(6<<29))
    cpu.step()
    cpu.memory[32:48]=ext128(3,0x1A,4,1,0,w1=(6<<29))
    cpu.step()
    assert u32(cpu.vector[3][0]) == -2.0
    assert u32(cpu.vector[4][0]) == 1.5

def test_vector_floating_point_conversions():
    import struct
    cpu=CorelessCPU()
    cpu.vector_vl=2
    def f32(x): return int.from_bytes(struct.pack("<f", x), "little")
    cpu.vector[1][:2]=[f32(1.5), f32(-2.5)]
    # FP32 -> INT16, signed conversion.
    cpu.memory[0:16]=ext128(3,0x17,2,1,0,w1=(6<<29)|(1<<0)|(1<<11))
    cpu.step()
    assert cpu.vector[2][:2] == [1,0xFFFE]
    # FP32 -> FP16.
    cpu.vector[1][:2]=[f32(1.5), f32(2.25)]
    cpu.memory[16:32]=ext128(3,0x17,3,1,0,w1=(6<<29)|(4<<11))
    cpu.step()
    assert cpu.vector[3][:2] == [0x3E00,0x4080]
    # FP16 -> FP32.
    cpu.vector[1][:2]=[0x3E00,0x4080]
    cpu.memory[32:48]=ext128(3,0x17,4,1,0,w1=(4<<29)|(6<<11))
    cpu.step()
    assert [struct.unpack("<f", x.to_bytes(4,"little"))[0] for x in cpu.vector[4][:2]] == [1.5,2.25]

def test_vector_integer_ops_reductions_and_scalar_forms():
    cpu=CorelessCPU()
    cpu.vector_vl=4
    cpu.vector[1][:4]=[8, 3, 12, 4]
    cpu.vector[2][:4]=[2, 5, 3, 2]
    cpu.memory[0:16]=ext128(3,0x03,3,1,2,w1=0)
    cpu.step(); assert cpu.vector[3][:4]==[4,0,4,2]
    cpu.memory[16:32]=ext128(3,0x0F,4,1,2,w1=0)
    cpu.step(); assert cpu.vector[4][:4]==[0,0,0,0]
    cpu.memory[32:48]=ext128(3,0x18,5,1,0,w1=0)
    cpu.step(); assert cpu.r[5]==27
    cpu.r[6]=9
    cpu.memory[48:64]=ext128(3,0x23,6,6,0,w1=0)
    cpu.step(); assert cpu.vector[6][:4]==[9,9,9,9]
    cpu.r[7]=2
    cpu.memory[64:80]=ext128(3,0x24,7,6,7,w1=0)
    cpu.step(); assert cpu.r[7]==9

def test_vector_memory_load_store_and_masked_access():
    cpu=CorelessCPU(memory_size=0x2000)
    cpu.vector_vl=4
    cpu.r[1]=0x100
    cpu.r[2]=4
    cpu.memory[0x100:0x110]=b"abcdefghijklmnop"
    cpu.memory[0:16]=ext128(3,0x1E,3,1,2,w1=(0<<29))
    cpu.step(); assert cpu.vector[3][:4]==[ord("a"),ord("e"),ord("i"),ord("m")]
    cpu.vector_mask[0]=0b0101
    cpu.vector[3][:4]=[9,9,9,9]
    cpu.memory[16:32]=ext128(3,0x1E,3,1,2,w1=(0<<29)|(1<<22))
    cpu.step(); assert cpu.vector[3][:4]==[ord("a"),9,ord("i"),9]


def test_vector_extended_ops():
    cpu=CorelessCPU(); cpu.vector_vl=4
    cpu.vector[1][:4]=[1,2,3,4]; cpu.vector[2][:4]=[10,20,30,40]
    cpu.vector[3][:4]=[100,100,100,100]
    # VSEL: active mask selects vs1; inactive lanes select vs2 in zeroing form.
    cpu.vector_mask[0]=0b0101
    cpu.memory[0:16]=ext128(3,0x12,4,1,2,w1=(0<<29)|(1<<22))
    cpu.step(); assert cpu.vector[4][:4]==[1,20,3,40]
    # VFMA/VFMS use the destination as the accumulator.
    cpu.vector[4][:4]=[1,1,1,1]
    cpu.memory[16:32]=ext128(3,0x13,4,1,2,w1=0)
    cpu.step(); assert cpu.vector[4][:4]==[11,41,91,161]
    cpu.vector[4][:4]=[100,100,100,100]
    cpu.memory[32:48]=ext128(3,0x14,4,1,2,w1=0)
    cpu.step(); assert cpu.vector[4][:4]==[90,60,10,196]
    # Indexed load and shuffle use per-lane indices/offsets.
    cpu.vector[5][:4]=[0,2,4,6]
    cpu.r[6]=0x100
    cpu.memory[0x100:0x108]=bytes([9,0,8,0,7,0,6,0])
    cpu.memory[48:64]=ext128(3,0x20,6,6,5,w1=(1<<29))
    cpu.step(); assert cpu.vector[6][:4]==[9,8,7,6]
    cpu.vector[5][:4]=[3,2,1,0]
    cpu.memory[64:80]=ext128(3,0x22,7,6,5,w1=0)
    cpu.step(); assert cpu.vector[7][:4]==[6,7,8,9]
    # VCONV: destination type is selected by operation mode; flag bit 0
    # selects signed source interpretation and bit 1 enables saturation.
    cpu.vector[1][:4]=[300,128,127,5]
    cpu.memory[80:96]=ext128(3,0x17,8,1,0,w1=(1<<29)|(0<<11)|0x2)
    cpu.step(); assert cpu.vector[8][:4]==[255,128,127,5]
    cpu.memory[96:112]=ext128(3,0x17,9,1,0,w1=(1<<29)|(0<<11)|0x3)
    cpu.step(); assert cpu.vector[9][:4]==[127,127,127,5]
    # Strided VLOAD/VSTORE use rs1 as base and rs2 as byte stride.
    cpu.r[10]=0x200
    cpu.r[11]=4
    cpu.memory[0x200:0x210]=bytes([1,0,0,0,2,0,0,0,3,0,0,0,4,0,0,0])
    cpu.memory[112:128]=ext128(3,0x1E,10,10,11,w1=2<<29)
    cpu.step(); assert cpu.vector[10][:4]==[1,2,3,4]
    cpu.vector_mask[1]=0b0101
    cpu.vector[10][:4]=[9,9,9,9]
    cpu.memory[128:144]=ext128(3,0x1F,10,10,11,w1=(2<<29)|(1<<22)|(1<<16))
    cpu.step()
    assert list(cpu.memory[0x200:0x210])==[9,0,0,0,2,0,0,0,9,0,0,0,4,0,0,0]



def test_matrix_mconv_signed_reduction_and_clamp():
    cpu=CorelessCPU()
    cpu.matrix_shape=(2,2,2)
    cpu.matrix[1][0][:2]=[0xFD, 0x04]
    cpu.matrix[1][1][:2]=[0xFD, 0x04]
    cpu.memory[0:16]=ext128(4,0x08,2,1,0,w1=(0<<29)|(1<<26)|(1<<22))
    cpu.step()
    assert cpu.matrix[2][0][:2]==[0xFFFD,4] and cpu.matrix[2][1][:2]==[0xFFFD,4]
    cpu.memory[16:32]=ext128(4,0x0D,3,1,0,w1=(0<<29)|(1<<22))
    cpu.step()
    assert cpu.r[3] == 2
    cpu.memory[32:48]=ext128(4,0x0E,1,1,0,w1=(0<<29)|(1<<22),w3=(0xFFFE & 0xFFFF)|((3 & 0xFFFF)<<16))
    cpu.step()
    assert cpu.matrix[1][0][:2]==[0xFE,3] and cpu.matrix[1][1][:2]==[0xFE,3]


def test_matrix_rectangular_transpose():
    cpu=CorelessCPU()
    cpu.memory[0:16]=ext128(4,0x07,2,1,0,w1=(3<<23))
    cpu.matrix[1][0][:16]=list(range(16))
    cpu.matrix[1][1][:16]=list(range(16,32))
    cpu.step()
    assert cpu.matrix[2][0][0:2] == [0,16]
    assert cpu.matrix[2][1][0:2] == [1,17]


def test_matrix_mmdot_rejects_floating_point_types():
    cpu=CorelessCPU()
    cpu.memory[0:16]=ext128(4,0x02,3,1,2,w1=(6<<29)|(6<<26))
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x011


def test_matrix_shape_resource_fault_is_precise():
    cpu=CorelessCPU()
    cpu.memory[0:16]=ext128(4,0x00,3,1,2,w1=(6<<23))
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x014
    assert cpu.instret == 0


def test_matrix_memory_alignment_fault_is_precise():
    cpu=CorelessCPU()
    cpu.matrix_shape=(2,2,2)
    cpu.r[1]=0x101
    cpu.memory[0:16]=ext128(4,0x09,2,1,0,w1=(1<<29),w2=2|(2<<16))
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x006
    assert cpu.matrix[2][0][:2] == [0,0]

def test_matrix_memory_faults_are_precise():
    # A fault in a later tile element must not expose a partial MLOAD/MSTORE.
    cpu=CorelessCPU(memory_size=0x1000)
    cpu.matrix_shape=(2,2,2)
    cpu.r[1]=0x0ffd
    cpu.matrix[1][0][:2]=[9,8]
    cpu.matrix[1][1][:2]=[7,6]
    cpu.memory[0x0ffd:0x1000]=bytes([1,2,3])
    cpu.memory[0:16]=ext128(4,0x09,2,1,0,w1=0,w2=1|(2<<16))
    cpu.step()
    assert cpu.csrs[0x005] & 0xFFFF == 0x007
    assert cpu.matrix[2][0][:2] == [0,0]
    assert cpu.matrix[2][1][:2] == [0,0]

    cpu2=CorelessCPU(memory_size=0x1000)
    cpu2.matrix_shape=(2,2,2)
    cpu2.r[1]=0x0ffd
    cpu2.matrix[1][0][:2]=[9,8]
    cpu2.matrix[1][1][:2]=[7,6]
    cpu2.memory[0x0ffd:0x1000]=bytes([1,2,3])
    cpu2.memory[0:16]=ext128(4,0x0A,1,1,0,w1=0,w2=1|(2<<16))
    cpu2.step()
    assert cpu2.csrs[0x005] & 0xFFFF == 0x007
    assert bytes(cpu2.memory[0x0ffd:0x1000]) == bytes([1,2,3])


def test_matrix_transform_and_data_movement():
    cpu=CorelessCPU()
    cpu.matrix_shape=(2,2,2)
    cpu.matrix[1][0][:2]=[1,2]
    cpu.matrix[1][1][:2]=[3,4]

    # MTRANS writes the transposed architectural tile.
    cpu.memory[0:16]=ext128(4,0x07,2,1,0,w1=0)
    cpu.step()
    assert cpu.matrix[2][0][:2] == [1,3]
    assert cpu.matrix[2][1][:2] == [2,4]

    # MCONV sign-extends INT8 values into INT16.
    cpu.matrix[1][0][:2]=[0xFF,0x7F]
    cpu.matrix[1][1][:2]=[0x80,0x01]
    cpu.memory[16:32]=ext128(4,0x08,3,1,0,w1=(0<<29)|(1<<26)|(1<<22))
    cpu.step()
    assert cpu.matrix[3][0][:2] == [0xFFFF,0x007F]
    assert cpu.matrix[3][1][:2] == [0xFF80,0x0001]

    # MBROADCAST, MREDUCE, and MCLAMP operate on the active tile shape.
    cpu.r[4]=9
    cpu.memory[32:48]=ext128(4,0x0C,4,4,0,w1=(0<<29)|(0<<26))
    cpu.step()
    assert cpu.matrix[4][0][:2] == [9,9] and cpu.matrix[4][1][:2] == [9,9]
    cpu.memory[48:64]=ext128(4,0x0D,5,4,0,w1=0)
    cpu.step()
    assert cpu.r[5] == 36
    cpu.matrix[4][0][:2]=[-2 & 0xFF, 5]
    cpu.matrix[4][1][:2]=[12, 20]
    cpu.memory[64:80]=ext128(4,0x0E,6,4,0,w1=(1<<22),w3=(0xFFFE)|((10 & 0xFFFF)<<16))
    cpu.step()
    assert cpu.matrix[6][0][:2] == [0xFE,5]
    assert cpu.matrix[6][1][:2] == [10,10]
