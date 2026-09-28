"""Coreless process manager with page-table-backed address spaces.

The reference runtime now models the architectural protection boundary:
each process gets a private physical code/stack allocation and a private
flat page-table root. Processes execute with USER privilege and the MMU
translates their common user virtual layout to their private physical pages.
"""
from dataclasses import dataclass, field

PAGE_SIZE = 1 << 12
USER_BASE = 0x10000
STACK_SIZE = PAGE_SIZE
REGION_SIZE = 1 << 16
PHYS_RESERVED = 0x4000


def align_up(value, alignment=PAGE_SIZE):
    return (value + alignment - 1) & ~(alignment - 1)


@dataclass
class AddressSpace:
    base: int
    size: int
    code_base: int
    stack_base: int
    stack_size: int
    page_table_root: int
    code_phys_base: int
    stack_phys_base: int
    permissions: dict = field(default_factory=lambda: {"code": "rx", "stack": "rw"})


@dataclass
class Process:
    pid: int
    name: str
    program: bytes = b""
    state: str = "ready"
    pc: int = 0
    sp: int = 0
    registers: list = field(default_factory=lambda: [0] * 32)
    parent: int = 0
    exit_code: int = 0
    ticks: int = 0
    address_space: AddressSpace = None
    privilege: int = 0
    root: int = 0
    asid: int = 0
    tlbctl: int = 0


class ProcessManager:
    PAGE_SIZE = PAGE_SIZE
    STACK_SIZE = STACK_SIZE
    REGION_SIZE = REGION_SIZE
    USER_BASE = USER_BASE
    PHYS_RESERVED = PHYS_RESERVED

    def __init__(self, machine):
        self.machine = machine
        self.processes = {}
        self.next_pid = 1
        self.current = None
        self.next_phys = self.PHYS_RESERVED

    def _alloc_phys(self, size):
        size = align_up(size)
        base = align_up(self.next_phys)
        end = base + size
        if end > len(self.machine.cpu.memory):
            raise MemoryError("no physical memory available for process")
        self.next_phys = end
        return base

    def _pte(self, root, virtual_page, physical_page, read, write, execute, user=True):
        flags = 1
        if read:
            flags |= 1 << 1
        if write:
            flags |= 1 << 2
        if execute:
            flags |= 1 << 3
        if user:
            flags |= 1 << 4
        flags |= 1 << 6  # accessed
        # Normal cacheable memory type = 0.
        pte = ((physical_page >> 12) << 12) | flags
        addr = root + virtual_page * 8
        if addr + 8 > len(self.machine.cpu.memory):
            raise MemoryError("page table outside physical memory")
        self.machine.cpu.memory[addr:addr + 8] = pte.to_bytes(8, "little")

    def _build_page_table(self, root, code_phys, code_size, stack_phys, stack_size):
        cpu = self.machine.cpu
        # A root is a flat baseline table indexed by virtual page number.
        # Clear the portion that can cover this process's user layout.
        max_vpn = (USER_BASE + max(REGION_SIZE, code_size + stack_size)) >> 12
        clear_end = root + (max_vpn + 1) * 8
        if clear_end > len(cpu.memory):
            raise MemoryError("page table outside physical memory")
        cpu.memory[root:clear_end] = b"\x00" * (clear_end - root)

        code_pages = align_up(max(code_size, 1)) // PAGE_SIZE
        for i in range(code_pages):
            self._pte(root, (USER_BASE >> 12) + i,
                      code_phys + i * PAGE_SIZE, True, False, True)

        stack_base = USER_BASE + max(REGION_SIZE, align_up(code_size) + stack_size) - stack_size
        stack_pages = align_up(stack_size) // PAGE_SIZE
        for i in range(stack_pages):
            self._pte(root, (stack_base >> 12) + i,
                      stack_phys + i * PAGE_SIZE, True, True, False)

    def _allocate_space(self, program_size):
        code_size = align_up(max(program_size, 1))
        size = max(self.REGION_SIZE, code_size + self.STACK_SIZE)
        # All processes share the same virtual layout but not the same
        # physical pages. This makes address-space switching explicit.
        root = self._alloc_phys(PAGE_SIZE)
        code_phys = self._alloc_phys(code_size)
        stack_phys = self._alloc_phys(self.STACK_SIZE)
        stack_base = self.USER_BASE + size - self.STACK_SIZE
        self._build_page_table(root, code_phys, code_size, stack_phys, self.STACK_SIZE)
        return AddressSpace(
            USER_BASE, size, USER_BASE, stack_base, self.STACK_SIZE,
            root, code_phys, stack_phys
        )

    def create(self, name, program=b"", parent=0):
        p = Process(self.next_pid, name, bytes(program), parent=parent)
        p.address_space = self._allocate_space(len(p.program))
        p.pc = p.address_space.code_base
        p.sp = p.address_space.stack_base + p.address_space.stack_size
        p.root = p.address_space.page_table_root
        p.asid = p.pid
        self.processes[p.pid] = p
        self.next_pid += 1
        return p

    def _save(self, p):
        cpu = self.machine.cpu
        p.pc = cpu.pc
        p.sp = cpu.sp
        p.registers = cpu.r[:]
        p.registers[0] = 0
        p.privilege = cpu.privilege
        p.root = cpu.csrs[0x007]
        p.asid = cpu.csrs[0x008]
        p.tlbctl = cpu.csrs[0x009]
        p.ticks += cpu.cycle

    def _restore(self, p):
        cpu = self.machine.cpu
        cpu.r = p.registers[:]
        cpu.r[0] = 0
        cpu.pc = p.pc or p.address_space.code_base
        cpu.sp = p.sp or (p.address_space.stack_base + p.address_space.stack_size)
        cpu.privilege = p.privilege
        cpu.csrs[0x000] = p.privilege
        cpu.csrs[0x007] = p.root or p.address_space.page_table_root
        cpu.csrs[0x008] = p.asid or p.pid
        cpu.csrs[0x009] = p.tlbctl or 1
        cpu.tlb.clear()
        cpu.halted = False

    def _enter_user(self, p):
        cpu = self.machine.cpu
        cpu.privilege = 0
        cpu.csrs[0x000] = 0
        cpu.csrs[0x007] = p.address_space.page_table_root
        cpu.csrs[0x008] = p.pid
        cpu.csrs[0x009] = 1
        cpu.tlb.clear()
        cpu.pc = p.address_space.code_base
        cpu.sp = p.address_space.stack_base + p.address_space.stack_size
        cpu.halted = False

    def start(self, pid, max_steps=100000):
        p = self.processes[pid]
        cpu = self.machine.cpu
        if p.state in ("exited", "killed"):
            return p

        code_start = p.address_space.code_phys_base
        cpu.memory[code_start:code_start + len(p.program)] = p.program
        p.state = "running"
        self.current = pid
        self._enter_user(p)
        self.machine.booted = True
        before = cpu.cycle
        steps = self.machine.run(max_steps)
        p.ticks += cpu.cycle - before
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
            self.machine.cpu.halted = True
            self.current = None

    def wait(self, parent_pid=0):
        for p in self.processes.values():
            if p.parent == parent_pid and p.state in ("exited", "killed"):
                return p
        return None

    def list(self):
        return list(self.processes.values())
