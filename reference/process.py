"""Coreless process manager with explicit address-space and scheduling state."""
from dataclasses import dataclass, field

@dataclass
class AddressSpace:
    base: int
    size: int
    code_base: int
    stack_base: int
    stack_size: int
    permissions: dict = field(default_factory=lambda: {"code": "rx", "stack": "rw"})

@dataclass
class Process:
    pid: int
    name: str
    program: bytes = b""
    state: str = "ready"
    pc: int = 0
    registers: list = field(default_factory=lambda: [0] * 32)
    parent: int = 0
    exit_code: int = 0
    ticks: int = 0
    address_space: AddressSpace = None

class ProcessManager:
    REGION_SIZE = 1 << 16
    STACK_SIZE = 1 << 12

    def __init__(self, machine):
        self.machine = machine
        self.processes = {}
        self.next_pid = 1
        self.current = None
        self.next_base = 0

    def _allocate_space(self, program_size):
        size = max(self.REGION_SIZE, program_size + self.STACK_SIZE)
        base = self.next_base
        if base + size > len(self.machine.cpu.memory):
            raise MemoryError("no process address space available")
        self.next_base += size
        return AddressSpace(base, size, base, base + size - self.STACK_SIZE, self.STACK_SIZE)

    def create(self, name, program=b"", parent=0):
        p = Process(self.next_pid, name, bytes(program), parent=parent)
        p.address_space = self._allocate_space(len(p.program))
        self.processes[p.pid] = p
        self.next_pid += 1
        return p

    def _save(self, p):
        cpu = self.machine.cpu
        p.pc = cpu.pc
        p.registers = cpu.r[:]
        p.registers[0] = 0
        p.ticks += cpu.cycle

    def _restore(self, p):
        cpu = self.machine.cpu
        cpu.r = p.registers[:]
        cpu.r[0] = 0
        cpu.pc = p.pc
        cpu.sp = p.address_space.stack_base + p.address_space.stack_size
        cpu.halted = False

    def start(self, pid, max_steps=100000):
        p = self.processes[pid]
        cpu = self.machine.cpu
        cpu.memory[p.address_space.base:p.address_space.base + len(p.program)] = p.program
        p.pc = p.address_space.code_base
        p.state = "running"
        self.current = pid
        self._restore(p)
        self.machine.booted = True
        steps = self.machine.run(max_steps)
        p.ticks += steps
        self._save(p)
        if cpu.halted:
            p.state = "exited"
        else:
            p.state = "ready"
        self.current = None
        return p

    def schedule_once(self, quantum=1000):
        ready = [p for p in self.processes.values() if p.state == "ready"]
        if not ready:
            return None
        return self.start(ready[0].pid, quantum)

    def spawn(self, name, program=b"", parent=0, start=False):
        p = self.create(name, program, parent)
        if start:
            self.start(p.pid)
        return p

    def kill(self, pid, code=-1):
        p = self.processes[pid]
        p.state = "killed"
        p.exit_code = code
        if self.current == pid:
            self.current = None

    def wait(self, parent_pid=0):
        for p in self.processes.values():
            if p.parent == parent_pid and p.state in ("exited", "killed"):
                return p
        return None

    def list(self):
        return list(self.processes.values())
