import sys
sys.path.insert(0, ".")
from encoding import encode_syscall
from machine_runtime import CorelessMachine
from os_runtime import CorelessOS
from core import USER, SUPERVISOR

def test_syscall_enters_supervisor_and_returns_to_user():
    os = CorelessOS(CorelessMachine(4096, 1)).run()
    cpu = os.machine.cpu
    os.current_pid = 7
    cpu.privilege = USER
    cpu.csrs[0x000] = USER
    cpu.csrs[0x003] = 0x100
    cpu.memory[0:4] = encode_syscall(13).to_bytes(4, "little")
    os.machine.booted = True

    observed = []
    original = os._syscall
    def observe(c, number):
        observed.append((c.privilege, c.csrs[0x004], c.csrs[0x005], number))
        return original(c, number)
    os._syscall = observe

    os.machine.step()

    assert observed[0][0] == SUPERVISOR
    assert observed[0][1] == 0
    assert (observed[0][2] & ((1 << 56) - 1)) == 0x019
    assert observed[0][3] == 13
    assert cpu.privilege == USER
    assert cpu.pc == 4
    assert cpu.read_reg(1) == 7

def test_syscall_uses_supervisor_trap_hook():
    os = CorelessOS(CorelessMachine(4096, 1)).run()
    cpu = os.machine.cpu
    cpu.privilege = USER
    cpu.csrs[0x000] = USER
    cpu.memory[0:4] = encode_syscall(15).to_bytes(4, "little")
    os.machine.booted = True

    assert cpu.supervisor_trap_handler is not None
    assert cpu.syscall_handler is None
    os.machine.step()
    assert cpu.privilege == USER
    assert cpu.pc == 4
    assert cpu.read_reg(1) == 4096
