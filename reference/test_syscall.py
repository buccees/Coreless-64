import sys
sys.path.insert(0, ".")
from encoding import encode_syscall
from machine_runtime import CorelessMachine
from os_runtime import CorelessOS

def test_native_syscalls():
    os = CorelessOS(CorelessMachine(4096, 2)).run()
    cpu = os.machine.cpu
    cpu.memory[0:4] = encode_syscall(13).to_bytes(4, "little")
    os.current_pid = 7
    os.machine.booted = True
    os.machine.step()
    assert cpu.read_reg(1) == 7

    cpu.pc = 4
    cpu.memory[4:8] = encode_syscall(15).to_bytes(4, "little")
    os.machine.step()
    assert cpu.read_reg(1) == 4096

    cpu.pc = 8
    cpu.memory[8:12] = encode_syscall(16).to_bytes(4, "little")
    os.machine.step()
    assert cpu.read_reg(1) == 2

    cpu.pc = 12
    cpu.memory[12:16] = encode_syscall(17).to_bytes(4, "little")
    os.machine.step()
    assert cpu.read_reg(1) >= 1

def test_syscall_exit_stops_execution():
    os = CorelessOS(CorelessMachine(4096, 1)).run()
    cpu = os.machine.cpu
    cpu.memory[0:4] = encode_syscall(0).to_bytes(4, "little")
    os.machine.booted = True
    os.machine.step()
    assert cpu.halted
    assert cpu.read_reg(1) == 0

def test_file_network_display_syscalls():
    os = CorelessOS(CorelessMachine(8192, 1)).run()
    cpu = os.machine.cpu
    os.machine.filesystem.write("/data", b"coreless-data")
    os.current_pid = 1

    cpu.memory[256:261] = b"/data"
    cpu.write_reg(2, 256)
    cpu.write_reg(3, 5)
    cpu.memory[0:4] = encode_syscall(3).to_bytes(4, "little")
    os.machine.booted = True
    os.machine.step()
    handle = cpu.read_reg(1)
    assert handle >= 3

    cpu.write_reg(2, handle)
    cpu.write_reg(3, 100)
    cpu.write_reg(4, 8)
    cpu.pc = 4
    cpu.memory[4:8] = encode_syscall(1).to_bytes(4, "little")
    os.machine.step()
    assert cpu.read_reg(1) == 8
    assert bytes(cpu.memory[100:108]) == b"coreless"

    cpu.write_reg(2, 100)
    cpu.write_reg(3, 5)
    cpu.memory[400:404] = b"peer"
    cpu.write_reg(4, 400)
    cpu.write_reg(5, 4)
    cpu.pc = 8
    cpu.memory[8:12] = encode_syscall(18).to_bytes(4, "little")
    os.machine.step()
    assert cpu.read_reg(1) == 5

    cpu.write_reg(2, 64)
    cpu.write_reg(3, 32)
    cpu.pc = 12
    cpu.memory[12:16] = encode_syscall(24).to_bytes(4, "little")
    os.machine.step()
    assert cpu.read_reg(1) == 0

    cpu.pc = 16
    cpu.write_reg(2, 0)
    cpu.memory[16:20] = encode_syscall(25).to_bytes(4, "little")
    os.machine.step()
    assert cpu.read_reg(1) == 0
