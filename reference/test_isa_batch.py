import sys, struct, math, tempfile
import pytest
sys.path.insert(0, ".")

from core import CorelessCPU, MACHINE, SUPERVISOR, USER
from encoding import (
    OP_ALUR, OP_ATOMIC, OP_ESCAPE, OP_EXT128,
    decode, decode_stream, instruction_length, IllegalEncoding,
)
from machine_runtime import CorelessMachine


def word(op, rd=0, rs1=0, rs2=0, f=0):
    return (op << 27) | (rd << 22) | (rs1 << 17) | (rs2 << 12) | f


def sysword(rd, rs1, f, operand=0):
    return (6 << 27) | (rd << 22) | (rs1 << 17) | ((operand & 0x7ff) << 5) | f


def ext128(cls, op, rd=0, rs1=0, rs2=0, w1=0, w2=0, w3=0):
    header = (OP_EXT128 << 27) | (cls << 23) | (op << 17) | (rd << 12) | (rs1 << 7) | (rs2 << 2) | 2
    return b"".join(x.to_bytes(4, "little") for x in (header, w1, w2, w3))


def test_base_decoder_rejects_reserved_primary_and_function_fields():
    with pytest.raises(IllegalEncoding):
        decode((OP_ESCAPE << 27))
    with pytest.raises(IllegalEncoding):
        decode((OP_ALUR << 27) | (21 << 5))
    with pytest.raises(IllegalEncoding):
        decode((2 << 27) | (7 << 14))
    with pytest.raises(IllegalEncoding):
        decode((3 << 27) | (4 << 14))


def test_atomic_decoder_accepts_all_defined_orderings_and_rejects_reserved():
    for ordering in range(5):
        raw = (OP_ATOMIC << 27) | (1 << 22) | (2 << 17) | (3 << 12) | (ordering << 9)
        assert decode(raw)[0] == "ATOMIC"
    with pytest.raises(IllegalEncoding):
        decode((OP_ATOMIC << 27) | (5 << 9))
    with pytest.raises(IllegalEncoding):
        decode((OP_ATOMIC << 27) | 11)


def test_atomic_cas_failure_is_non_destructive():
    cpu = CorelessCPU()
    cpu.r[1] = 0x100
    cpu.r[2] = 7
    cpu.r[3] = 9
    cpu.memory[0x100:0x108] = (5).to_bytes(8, "little")
    raw = (OP_ATOMIC << 27) | (4 << 22) | (1 << 17) | (2 << 12) | (3 << 4) | 1
    cpu.memory[0:4] = raw.to_bytes(4, "little")
    cpu.step()
    assert cpu.r[4] == 5
    assert int.from_bytes(cpu.memory[0x100:0x108], "little") == 5


def test_csr_access_faults_and_retx_restore_trap_state():
    cpu = CorelessCPU()
    cpu.csrs[0x003] = 0x100
    cpu.memory[0:4] = sysword(1, 0, 8, 0x3FF).to_bytes(4, "little")
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x003
    assert cpu.csrs[0x004] == 0
    assert cpu.pc == 0x100

    cpu.memory[0x100:0x104] = sysword(0, 0, 4).to_bytes(4, "little")
    cpu.step()
    assert cpu.pc == 0
    assert cpu.privilege == MACHINE


def test_interrupt_entry_and_retx_are_precise():
    cpu = CorelessCPU()
    cpu.csrs[0x003] = 0x200
    cpu.csrs[0x001] = 1 << 3
    cpu.request_interrupt(3)
    assert cpu.step()
    assert cpu.pc == 0x200
    assert cpu.csrs[0x005] & (1 << 63)
    assert (cpu.csrs[0x005] & 0xFFFF) == 3
    cpu.memory[0x200:0x204] = sysword(0, 0, 4).to_bytes(4, "little")
    cpu.step()
    assert cpu.pc == 0
    assert cpu.csrs[0x001] == (1 << 3)


def test_reset_state_is_architecturally_deterministic():
    a, b = CorelessCPU(), CorelessCPU()
    assert a.r == b.r == [0] * 32
    assert a.f == b.f == [0] * 32
    assert a.pc == b.pc == 0
    assert a.privilege == b.privilege == MACHINE
    assert a.vector == b.vector
    assert a.matrix == b.matrix
    assert a.csrs[0x00A] == 0
    assert a.csrs[0x00B] == 1
    assert a.csrs[0x01F] == 0x434C3634


def test_scalar_fp_nan_and_signed_zero_minmax():
    cpu = CorelessCPU()
    def f32(x):
        return int.from_bytes(struct.pack("<f", x), "little")
    cpu.f[1] = f32(float("nan"))
    cpu.f[2] = f32(2.0)
    cpu.memory[0:16] = ext128(2, 4, 3, 1, 2, w1=6 << 29)
    cpu.step()
    assert struct.unpack("<f", cpu.f[3].to_bytes(4, "little"))[0] == 2.0

    cpu.f[1] = f32(-0.0)
    cpu.f[2] = f32(+0.0)
    cpu.memory[16:32] = ext128(2, 4, 3, 1, 2, w1=6 << 29)
    cpu.step()
    assert cpu.f[3] == f32(-0.0)

    cpu.memory[32:48] = ext128(2, 5, 4, 1, 2, w1=6 << 29)
    cpu.step()
    assert cpu.f[4] == f32(+0.0)


def test_vector_and_matrix_architectural_state_survives_checkpoint():
    with tempfile.TemporaryDirectory() as td:
        path = td + "/coreless.img"
        m = CorelessMachine(memory_size=4096, storage_path=path)
        m.boot()
        c = m.cpu
        c.vector_vl = 4
        c.vector_vstart = 2
        c.vector_mask[3] = 0xA
        c.vector[7][:4] = [11, 22, 33, 44]
        c.matrix_shape = (2, 2, 2)
        c.matrix[5][0][:2] = [101, 102]
        c.matrix[5][1][:2] = [103, 104]
        m.checkpoint("isa-state")
        c.vector[7][:4] = [0, 0, 0, 0]
        c.vector_vstart = 0
        c.matrix[5][0][:2] = [0, 0]
        m.restore_checkpoint("isa-state")
        assert m.cpu.vector[7][:4] == [11, 22, 33, 44]
        assert m.cpu.vector_vstart == 2
        assert m.cpu.vector_mask[3] == 0xA
        assert m.cpu.matrix[5][0][:2] == [101, 102]
        assert m.cpu.matrix[5][1][:2] == [103, 104]


def test_decode_stream_preserves_mixed_base_and_extended_boundaries():
    base = word(0, 1, 0, 0, 0).to_bytes(4, "little")
    ext = ext128(3, 0x00, 2, 1, 0)
    out = decode_stream(base + ext + base)
    assert [(x[0], x[1]) for x in out] == [(0, 4), (4, 16), (20, 4)]
