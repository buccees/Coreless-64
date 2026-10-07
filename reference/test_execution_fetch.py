from core import CorelessCPU
from encoding import encode_extended_header


def test_fetch_instruction_returns_exact_base_boundary():
    cpu = CorelessCPU()
    cpu.memory[0:4] = (0).to_bytes(4, "little")
    length, words = cpu._fetch_instruction()
    assert length == 4
    assert len(words) == 1


def test_fetch_instruction_returns_exact_64_bit_boundary():
    cpu = CorelessCPU()
    header = encode_extended_header(2, 0, 1, 0, 0, 2, length=8)
    cpu.memory[0:8] = header.to_bytes(4, "little") + b"\x00\x00\x00\x00"
    length, words = cpu._fetch_instruction()
    assert length == 8
    assert len(words) == 2


def test_fetch_instruction_returns_exact_128_bit_boundary():
    cpu = CorelessCPU()
    header = encode_extended_header(3, 0x23, 1, 0, 0, 2, length=16)
    cpu.memory[0:16] = header.to_bytes(4, "little") + bytes(12)
    length, words = cpu._fetch_instruction()
    assert length == 16
    assert len(words) == 4
