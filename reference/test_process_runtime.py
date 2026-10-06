import sys
sys.path.insert(0, ".")
from app import hello_program
from machine_runtime import CorelessMachine
from process import ProcessManager
from loader import ProgramLoader
from core import CorelessTrap, USER


def test_scheduler_and_process_metadata():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    p = pm.create("hello", hello_program(), parent=7)
    assert p.pid == 1
    result = pm.start(p.pid)
    assert result.state == "exited"
    assert result.ticks > 0
    assert pm.wait(7).pid == 1


def test_corex64_executable_round_trip():
    machine = CorelessMachine(256 * 1024, 1)
    loader = ProgramLoader(machine)
    image = loader.make_executable(hello_program())
    result = loader.load_executable(image)
    assert result["entry"] == 0
    assert result["size"] == len(hello_program())


def test_processes_have_distinct_page_table_roots_and_physical_code():
    machine = CorelessMachine(512 * 1024, 1)
    pm = ProcessManager(machine)
    a = pm.create("a", hello_program())
    b = pm.create("b", hello_program())

    assert a.address_space.page_table_root != b.address_space.page_table_root
    assert a.address_space.code_phys_base != b.address_space.code_phys_base

    root_a = int.from_bytes(
        machine.cpu.memory[a.address_space.page_table_root + (a.address_space.code_base >> 12) * 8:
                           a.address_space.page_table_root + (a.address_space.code_base >> 12) * 8 + 8],
        "little")
    root_b = int.from_bytes(
        machine.cpu.memory[b.address_space.page_table_root + (b.address_space.code_base >> 12) * 8:
                           b.address_space.page_table_root + (b.address_space.code_base >> 12) * 8 + 8],
        "little")
    assert ((root_a >> 12) << 12) == a.address_space.code_phys_base
    assert ((root_b >> 12) << 12) == b.address_space.code_phys_base
    assert root_a != root_b


def test_user_code_is_execute_read_only():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    p = pm.create("hello", hello_program())
    pm._enter_user(p)

    assert machine.cpu.privilege == USER
    assert machine.cpu.csrs[0x007] == p.address_space.page_table_root

    try:
        machine.cpu.store_u(p.address_space.code_base, 1, 0xFF)
    except CorelessTrap as trap:
        assert trap.cause == "write_permission_fault"
    else:
        raise AssertionError("user code page was writable")


def test_process_create_accepts_corex64_entry_point():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    program = b"".join([
        (0x30000001).to_bytes(4, "little"),
        (0x30000001).to_bytes(4, "little"),
    ])
    image = ProgramLoader.make_executable(program, entry=4)
    p = pm.create("entry", image)
    assert p.program == program
    assert p.pc == p.address_space.code_base + 4


def test_process_replace_program_preserves_pid_and_uses_executable_entry():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    p = pm.create("exec", (0x30000001).to_bytes(4, "little"), parent=9)
    pid = p.pid
    image = ProgramLoader.make_executable(
        b"".join([
            (0x30000001).to_bytes(4, "little"),
            (0x30000001).to_bytes(4, "little"),
        ]),
        entry=4,
    )
    pm.replace_program(p, image)
    assert p.pid == pid
    assert p.parent == 9
    assert p.program == image[ProgramLoader.HEADER_SIZE:]
    assert p.pc == p.address_space.code_base + 4


def test_os_exec_transfers_to_executable_entry():
    from os_runtime import CorelessOS
    machine = CorelessMachine(256 * 1024, 1)
    os = CorelessOS(machine)
    p = os.processes.create("exec", (0x30000001).to_bytes(4, "little"))
    os.current_pid = p.pid
    os.processes._enter_user(p)
    path_addr = p.address_space.stack_base
    path = b"/new"
    for i, value in enumerate(path):
        machine.cpu.store_u(path_addr + i, 1, value)
    program = b"".join([
        (0x30000001).to_bytes(4, "little"),
        (0x30000001).to_bytes(4, "little"),
    ])
    machine.filesystem.write("/new", ProgramLoader.make_executable(program, entry=4))
    machine.cpu.write_reg(2, path_addr)
    machine.cpu.write_reg(3, len(path))
    os._syscall(machine.cpu, 10)
    assert p.program == program
    assert p.pc == p.address_space.code_base + 4
    assert machine.cpu.pc == p.pc
    assert os._exec_transfer is True


def test_process_load_image_materializes_replaced_executable():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    program = b"".join([
        (0x30000001).to_bytes(4, "little"),
        (0x30000001).to_bytes(4, "little"),
    ])
    image = ProgramLoader.make_executable(program, entry=4)
    p = pm.create("image", image)
    pm.load_image(p)
    start = p.address_space.code_phys_base
    assert bytes(machine.cpu.memory[start:start + len(program)]) == program


def test_process_load_image_clears_stale_tail():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    p = pm.create("image", b"\x01" * 8)
    start = p.address_space.code_phys_base
    machine.cpu.memory[start:start + 16] = b"\xaa" * 16
    pm.load_image(p)
    assert bytes(machine.cpu.memory[start:start + 8]) == b"\x01" * 8


def test_process_replace_program_reuses_sufficient_address_space():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    p = pm.create("exec", b"\x01" * 8)
    root = p.address_space.page_table_root
    code = p.address_space.code_phys_base
    next_phys = pm.next_phys
    pm.replace_program(p, b"\x02" * 4)
    assert p.address_space.page_table_root == root
    assert p.address_space.code_phys_base == code
    assert pm.next_phys == next_phys
    assert p.program == b"\x02" * 4


def test_process_replace_program_reclaims_old_address_space():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    p = pm.create("exec", b"\x01" * 8)
    old = p.address_space
    old_next = pm.next_phys
    pm.replace_program(p, b"\x02" * (32 * 1024))
    assert p.address_space.page_table_root != old.page_table_root
    assert pm.next_phys > old_next
    def covered(address, size):
        return any(base <= address and address + size <= base + length
                   for base, length in pm.free_phys)

    assert covered(old.page_table_root, 4096)
    assert covered(old.code_phys_base, old.stack_phys_base - old.code_phys_base)
    assert covered(old.stack_phys_base, old.stack_size)


def test_process_state_persists_reclaimed_physical_ranges():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    p = pm.create("exec", b"\x01" * 8)
    old = p.address_space
    pm.replace_program(p, b"\x02" * (32 * 1024))
    state = pm.save_state()

    restored = ProcessManager(machine)
    restored.restore_state(state)
    assert restored.free_phys == pm.free_phys
    assert old.page_table_root in [base for base, _ in restored.free_phys]


def test_reap_releases_completed_process_address_space():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    p = pm.create("reap", b"\x01" * 8)
    p.state = "exited"
    space = p.address_space
    assert pm.reap(p.pid) is p
    assert p.pid not in pm.processes
    assert pm.current is None
    assert pm.next_phys == space.page_table_root
    assert not pm.free_phys


def test_reap_rejects_live_process():
    machine = CorelessMachine(256 * 1024, 1)
    pm = ProcessManager(machine)
    p = pm.create("live", b"\x01" * 8)
    try:
        pm.reap(p.pid)
    except RuntimeError as exc:
        assert str(exc) == "cannot reap a running process"
    else:
        raise AssertionError("live process was reaped")


def test_process_allocation_failure_rolls_back_physical_ranges():
    machine = CorelessMachine(64 * 1024, 1)
    pm = ProcessManager(machine)
    before = (pm.next_phys, list(pm.free_phys))
    try:
        pm.create("too-large", b"\x00" * (64 * 1024))
    except MemoryError:
        pass
    else:
        raise AssertionError("oversized process allocation unexpectedly succeeded")
    assert (pm.next_phys, pm.free_phys) == before
