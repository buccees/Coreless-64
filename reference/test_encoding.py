import sys
sys.path.insert(0, ".")
import pytest
import struct
from core import CorelessCPU
from encoding import (
    OP_EXT64, OP_EXT128, OP_ESCAPE, IllegalEncoding,
    decode_extended_header, decode_stream, instruction_length,
    ExtendedInstruction, encode_extended_instruction, decode_extended_instruction,
    extended_payload_size,
)

def ext_header(cls, op=0, rd=0, rs1=0, rs2=0, fmt=2, *, length=128):
    prefix = OP_EXT64 if length == 64 else OP_EXT128
    return (
        (prefix << 27)
        | (cls << 23)
        | (op << 17)
        | (rd << 12)
        | (rs1 << 7)
        | (rs2 << 2)
        | fmt
    )

def ext64_header(cls, op=0, rd=0, rs1=0, rs2=0, fmt=2):
    return ext_header(cls, op, rd, rs1, rs2, fmt, length=64)

def test_variable_length_boundaries_and_truncation():
    assert instruction_length(0) == 4
    assert instruction_length(OP_EXT64 << 27) == 8
    assert instruction_length(OP_EXT128 << 27) == 16
    with pytest.raises(IllegalEncoding):
        instruction_length(OP_ESCAPE << 27)
    with pytest.raises(IllegalEncoding):
        decode_stream((OP_EXT128 << 27).to_bytes(4, "little"))
    with pytest.raises(IllegalEncoding):
        decode_stream(((OP_EXT128 << 27) | (2 << 23) | 2).to_bytes(4, "little") + b"\0" * 4)

def test_reserved_extended_class_and_format_rejected():
    with pytest.raises(IllegalEncoding):
        decode_extended_header(ext_header(9))
    # decode_stream validates framing; the execution engine validates the
    # extended format field.
    cpu = CorelessCPU()
    cpu.memory[0:16] = b"".join(x.to_bytes(4, "little") for x in (
        ext_header(2, fmt=1), 0, 0, 0
    ))
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x017

def test_extended_operation_reservation_rejected_by_cpu():
    cpu = CorelessCPU()
    cpu.memory[0:16] = b"".join(x.to_bytes(4, "little") for x in (
        ext_header(2, 0x3F), 0, 0, 0
    ))
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x002

def test_truncated_extended_instruction_traps_as_instruction_access_fault():
    cpu = CorelessCPU(memory_size=4096)
    cpu.memory[0:4] = ext_header(2).to_bytes(4, "little")
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x002

def test_64_bit_extended_scalar_fp_executes_and_advances_by_8():
    cpu = CorelessCPU()
    cpu.f[1] = int.from_bytes(struct.pack("<d", 1.5), "little")
    cpu.f[2] = int.from_bytes(struct.pack("<d", 2.25), "little")
    descriptor = (7 << 29)
    cpu.memory[0:8] = b"".join(
        x.to_bytes(4, "little") for x in (ext64_header(2, 0, 0, 1, 2), descriptor)
    )
    cpu.step()
    assert struct.unpack("<d", cpu.f[0].to_bytes(8, "little"))[0] == 3.75
    assert cpu.pc == 8
    assert cpu.instret == 1

def test_64_bit_extended_non_fp_class_is_not_silently_executed():
    cpu = CorelessCPU()
    cpu.memory[0:8] = b"".join(
        x.to_bytes(4, "little") for x in (ext64_header(0, 0), 0)
    )
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x002

def test_64_bit_extended_fp_operation_reservation_is_checked():
    cpu = CorelessCPU()
    cpu.memory[0:8] = b"".join(
        x.to_bytes(4, "little") for x in (ext64_header(2, 0x3F), 0)
    )
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x002


from encoding import ExtendedInstruction, encode_extended_instruction, decode_extended_instruction

def test_extended_instruction_round_trip_is_canonical():
    payload = bytes(range(12))
    encoded = encode_extended_instruction(4, 7, 3, 5, 6, 2, payload)
    decoded = decode_extended_instruction(encoded)
    assert decoded == ExtendedInstruction(16, 4, 7, 3, 5, 6, 2, payload)
    assert decoded.encode() == encoded

def test_extended_instruction_payload_size_is_architectural():
    with pytest.raises(IllegalEncoding):
        encode_extended_instruction(1, payload=b"\\0", length=8)
    with pytest.raises(IllegalEncoding):
        encode_extended_instruction(1, payload=b"\\0" * 12, length=8)
    with pytest.raises(IllegalEncoding):
        decode_extended_instruction((OP_EXT128 << 27).to_bytes(4, "little") + b"\\0" * 8)

def test_extended_instruction_rejects_base_length():
    with pytest.raises(IllegalEncoding):
        decode_extended_instruction((0).to_bytes(4, "little"))


def test_extended_64_instruction_round_trip_is_canonical():
    payload = (0x12345678).to_bytes(4, "little")
    encoded = encode_extended_instruction(0, 3, 31, 30, 29, 0, payload, length=8)
    decoded = decode_extended_instruction(encoded)
    assert decoded == ExtendedInstruction(8, 0, 3, 31, 30, 29, 0, payload)
    assert decoded.encode() == encoded


def test_extended_header_fields_are_validated_at_record_boundary():
    with pytest.raises(IllegalEncoding):
        ExtendedInstruction(8, 9, 0, 0, 0, 0, 0, b"\0" * 4)
    with pytest.raises(IllegalEncoding):
        ExtendedInstruction(8, 0, 0, 0x20, 0, 0, 0, b"\0" * 4)
    with pytest.raises(IllegalEncoding):
        ExtendedInstruction(8, 0, 0, 0, 0, 0, 4, b"\0" * 4)


def test_extended_payload_size_matches_length_contract():
    assert extended_payload_size(8) == 4
    assert extended_payload_size(16) == 12
    with pytest.raises(IllegalEncoding):
        extended_payload_size(4)
