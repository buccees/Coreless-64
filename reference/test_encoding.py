import sys
sys.path.insert(0, ".")
import pytest
from core import CorelessCPU
from encoding import (
    OP_EXT64, OP_EXT128, OP_ESCAPE, IllegalEncoding,
    decode_extended_header, decode_stream, instruction_length,
)

def ext_header(cls, op=0, fmt=2):
    return (
        (OP_EXT128 << 27)
        | (cls << 23)
        | (op << 17)
        | fmt
    )

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

def test_unsupported_64_bit_extended_form_is_rejected():
    cpu = CorelessCPU()
    cpu.memory[0:4] = (OP_EXT64 << 27).to_bytes(4, "little")
    cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x017
