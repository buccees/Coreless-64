"""Coreless process manager and cooperative scheduler."""
from dataclasses import dataclass, field

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

class ProcessManager:
    def __init__(self, machine):
        self.machine = machine
        self.processes = {}
        self.next_pid = 1
        self.current = None

    def create(self, name, program=b"", parent=0):
        p = Process(self.next_pid, name, bytes(program), parent=parent)
        self.processes[p.pid] = p
        self.next_pid += 1
        return p

    def start(self, pid, max_steps=100000):
        p = self.processes[pid]
        self.machine.load_program(p.program, 0)
        self.machine.booted = True
        p.state = "running"
        self.current = pid
        self.machine.cpu.halted = False
        steps = self.machine.run(max_steps)
        p.ticks += steps
        p.pc = self.machine.cpu.pc
        p.registers = self.machine.cpu.r[:]
        if self.machine.cpu.halted:
            p.state = "exited"
        else:
            p.state = "ready"
        return p

    def schedule_once(self, quantum=1000):
        ready = [p for p in self.processes.values() if p.state == "ready"]
        if not ready:
            return None
        p = ready[0]
        return self.start(p.pid, quantum)

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
