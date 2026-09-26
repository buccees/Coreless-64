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
