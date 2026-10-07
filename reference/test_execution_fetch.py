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


def test_truncated_extended_instruction_traps_before_retirement():
    cpu = CorelessCPU(memory_size=4096)
    cpu.csrs[0x003] = 0x100
    cpu.pc = 4092
    header = encode_extended_header(3, 0x23, 1, 0, 0, 2, length=16)
    cpu.memory[4092:4096] = header.to_bytes(4, "little")

    assert cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x000
    assert cpu.csrs[0x004] == 4092
    assert cpu.pc == 0x100
    assert cpu.instret == 0


def test_mixed_length_fetch_preserves_architectural_boundaries():
    cpu = CorelessCPU()
    base = (0).to_bytes(4, "little")
    ext = encode_extended_header(2, 0, 1, 0, 0, 2, length=8)
    cpu.load_program(base + ext.to_bytes(4, "little") + b"\x00\x00\x00\x00")

    length, words = cpu._fetch_instruction()
    assert length == 4 and len(words) == 1
    cpu.pc = 4
    length, words = cpu._fetch_instruction()
    assert length == 8 and len(words) == 2


def test_extended_fetch_traps_when_payload_lacks_execute_permission():
    cpu = CorelessCPU(memory_size=0x5000)
    cpu.csrs[0x003] = 0x400
    cpu.csrs[0x007] = 0x3000
    cpu.csrs[0x009] = 1
    cpu.pc = 0x0FFC

    # The 16-byte instruction straddles two virtual pages. The first page is
    # executable; the second is mapped but deliberately lacks execute permission.
    pte_exec = 1 | (1 << 1) | (1 << 3) | (1 << 12)
    pte_noexec = 1 | (1 << 1) | (2 << 12)
    cpu.memory[0x3000:0x3008] = pte_exec.to_bytes(8, "little")
    cpu.memory[0x3008:0x3010] = pte_noexec.to_bytes(8, "little")

    header = encode_extended_header(3, 0x23, 1, 0, 0, 2, length=16)
    cpu.memory[0x0FFC:0x1000] = header.to_bytes(4, "little")
    cpu.memory[0x1000:0x100C] = bytes(12)

    assert cpu.step()
    assert (cpu.csrs[0x005] & 0xFFFF) == 0x009
    assert cpu.csrs[0x004] == 0x0FFC
    assert cpu.csrs[0x006] == 0x1000
    assert cpu.pc == 0x400
    assert cpu.instret == 0
