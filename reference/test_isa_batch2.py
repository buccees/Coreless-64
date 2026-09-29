"""Second-wave Coreless-64 architectural conformance batch."""
import sys
sys.path.insert(0, ".")
import pytest

from core import CorelessCPU, USER, SUPERVISOR, MACHINE
from encoding import (
    ALUR, ALUI, BRANCH, JUMP, SYSTEM, LOAD,
    OP_ATOMIC, OP_EXT64, OP_EXT128, OP_ESCAPE,
    IllegalEncoding, decode, decode_stream, encode_r, encode_i,
    encode_syscall, instruction_length,
)
from machine_runtime import CorelessMachine


def expect_illegal(fn):
    with pytest.raises(IllegalEncoding):
        fn()


def test_every_defined_base_alu_operation_round_trips():
    for funct, name in ALUR.items():
        assert decode(encode_r(funct, 31, 30, 29)) == (name, 31, 30, 29)


def test_every_defined_immediate_operation_round_trips():
    for funct, name in ALUI.items():
        assert decode(encode_i(funct, 31, 30, -17)) == (name, 31, 30, -17)


def test_all_branch_functions_decode():
    for funct, name in BRANCH.items():
        w = (4 << 27) | (7 << 22) | (8 << 17) | (funct << 12) | ((-32) & 0xfff)
        assert decode(w) == (name, 7, 8, -32)


def test_all_jump_functions_decode_or_reject_reserved_fields():
    for funct, name in JUMP.items():
        if name == "RET":
            w = (5 << 27) | (funct << 12)
            assert decode(w) == ("RET", 0, 0, 0)
        else:
            w = (5 << 27) | (7 << 22) | (funct << 12) | 12
            assert decode(w)[0] == name


def test_all_system_functions_decode():
    for funct, name in SYSTEM.items():
        w = (6 << 27) | funct
        assert decode(w)[0] == name


def test_load_store_width_boundaries():
    for width, name in LOAD.items():
        w = (2 << 27) | (3 << 22) | (4 << 17) | (width << 14) | ((-1) & 0x3fff)
        assert decode(w) == (name, 3, 4, -1)
    for width, name in enumerate(("ST8", "ST16", "ST32", "ST64")):
        w = (3 << 27) | (3 << 22) | (4 << 17) | (width << 14) | 31
        assert decode(w) == (name, 3, 4, 31)


def test_reserved_primary_space_is_rejected():
    expect_illegal(lambda: decode((13 << 27)))
    expect_illegal(lambda: decode((31 << 27)))
    expect_illegal(lambda: instruction_length(OP_ESCAPE << 27))


def test_extended_header_reserved_classes_are_rejected():
    for cls in (9, 10, 15):
        w = (OP_EXT128 << 27) | (cls << 23) | 2
        expect_illegal(lambda w=w: __import__("encoding").decode_extended_header(w))


def test_extended_header_formats_are_visible_to_stream_decoder():
    for fmt in range(4):
        w = (OP_EXT128 << 27) | (3 << 23) | fmt
        payload = b"".join((i).to_bytes(4, "little") for i in range(3))
        out = decode_stream(w.to_bytes(4, "little") + payload)
        assert out[0][2][-1] == fmt


def test_syscall_encoding_covers_full_immediate_range():
    assert decode(encode_syscall(0))[0] == "SYSCALL"
    assert decode(encode_syscall(2047))[0] == "SYSCALL"
    expect_illegal(lambda: encode_syscall(2048))


def test_syscall_user_trap_round_trip_preserves_pc():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.csrs[0x000] = USER
    cpu.csrs[0x003] = 0x100
    cpu.memory[0:4] = encode_syscall(13).to_bytes(4, "little")
    cpu.step()
    assert cpu.privilege == SUPERVISOR
    assert cpu.csrs[0x004] == 0
    cpu.memory[0x100:0x104] = ((6 << 27) | 4).to_bytes(4, "little")
    cpu.step()
    assert cpu.privilege == USER
    assert cpu.pc == 0


def test_tlb_flush_privilege_boundaries():
    cpu = CorelessCPU()
    cpu.privilege = USER
    cpu.memory[0:4] = ((6 << 27) | 6).to_bytes(4, "little")
    cpu.step()
    assert (cpu.csrs[0x005] & 0xffff) != 0
    cpu.privilege = MACHINE
    cpu.pc = 0
    cpu.memory[0:4] = ((6 << 27) | 6).to_bytes(4, "little")
    cpu.step()
    assert cpu.pc == 4


def test_tlb_flush_va_privilege_boundaries():
    cpu = CorelessCPU()
    cpu.tlb[2] = 123
    cpu.r[1] = 2 << 12
    cpu.privilege = MACHINE
    cpu.memory[0:4] = ((6 << 27) | (1 << 22) | (1 << 17) | 7).to_bytes(4, "little")
    cpu.step()
    assert 2 not in cpu.tlb


def test_shared_machine_ram_is_visible_to_all_cpus():
    m = CorelessMachine(4096, 2)
    m.cpu.memory[128:136] = (0x1122334455667788).to_bytes(8, "little")
    assert int.from_bytes(m.cpus[1].memory[128:136], "little") == 0x1122334455667788
    m.cpus[1].memory[136:144] = (0xAABBCCDDEEFF0011).to_bytes(8, "little")
    assert int.from_bytes(m.cpu.memory[136:144], "little") == 0xAABBCCDDEEFF0011


def test_machine_cpu_identity_and_count_are_architectural():
    m = CorelessMachine(4096, 3)
    assert [c.csrs[0x00A] for c in m.cpus] == [0, 1, 2]
    assert [c.csrs[0x00B] for c in m.cpus] == [3, 3, 3]


def test_checkpoint_restores_each_cpu_independently():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        m = CorelessMachine(4096, 2, storage_path=td + "/machine.img")
        m.boot()
        m.cpus[0].pc = 0x40
        m.cpus[1].pc = 0x80
        m.cpus[1].r[5] = 1234
        m.checkpoint("cpus")
        m.cpus[0].pc = 0
        m.cpus[1].pc = 0
        m.cpus[1].r[5] = 0
        m.restore_checkpoint("cpus")
        assert m.cpus[0].pc == 0x40
        assert m.cpus[1].pc == 0x80
        assert m.cpus[1].r[5] == 1234
