import sys
sys.path.insert(0, ".")

from machine_runtime import CorelessMachine
from os_runtime import CorelessOS


def test_virtual_ram_persists_across_machine_restart(tmp_path):
    disk = tmp_path / "coreless.img"
    first = CorelessMachine(8192, storage_path=disk)
    first.boot()
    first.cpu.memory[4096:4100] = b"CL64"
    first.cpu.memory.flush()
    second = CorelessMachine(8192, storage_path=disk)
    assert bytes(second.cpu.memory[4096:4100]) == b"CL64"
    assert second.cpu.memory.size == 8192


def test_virtual_ram_is_sparse(tmp_path):
    disk = tmp_path / "coreless.img"
    machine = CorelessMachine(64 * 1024, storage_path=disk)
    assert not any(k.startswith("ram/ram/") for k in machine.storage.objects)
    machine.cpu.memory[0:4] = b"BOOT"
    machine.cpu.memory.flush()
    assert "ram/ram/0" in machine.storage.objects
    assert len(machine.storage.objects["ram/ram/0"]) == 4096


def test_cpus_share_coreless_ram(tmp_path):
    disk = tmp_path / "coreless.img"
    machine = CorelessMachine(8192, cpu_count=2, storage_path=disk)
    machine.boot()
    # Populate CPU1's view first; this catches the old per-CPU stale-cache bug.
    assert bytes(machine.cpus[1].memory[0:4]) == b"\x00\x00\x00\x00"
    machine.cpus[0].memory[0:4] = b"SHRD"
    assert machine.cpus[0].memory is machine.cpus[1].memory
    assert bytes(machine.cpus[1].memory[0:4]) == b"SHRD"
    machine.cpus[1].memory[4:8] = b"BACK"
    assert bytes(machine.cpus[0].memory[4:8]) == b"BACK"


def test_machine_state_persists_across_restart(tmp_path):
    disk = tmp_path / "coreless.img"
    first = CorelessMachine(8192, storage_path=disk)
    first.boot()
    first.cpu.r[7] = 0x12345678
    first.cpu.pc = 0x100
    first.cpu.sp = 0x1800
    first.cpu.cycle = 77
    first.cpu.instret = 55
    first.save_state()
    second = CorelessMachine(8192, storage_path=disk)
    assert second.booted is True
    assert second.cpu.r[7] == 0x12345678
    assert second.cpu.pc == 0x100
    assert second.cpu.sp == 0x1800
    assert second.cpu.cycle == 77
    assert second.cpu.instret == 55


def test_process_and_os_state_persist_across_restart(tmp_path):
    disk = tmp_path / "coreless.img"
    first = CorelessMachine(256 * 1024, storage_path=disk)
    os1 = CorelessOS(first)
    process = os1.processes.create("init", b"\x00\x00\x00\x00")
    os1.current_pid = process.pid
    os1.init_pid = process.pid
    os1.handles[7] = {"kind": "file", "path": "/state", "offset": 12}
    os1.desktop.open_window("saved", 200, 100)
    first.boot()
    first.save_state()
    second = CorelessMachine(256 * 1024, storage_path=disk)
    os2 = CorelessOS(second)
    assert os2.current_pid == process.pid
    assert os2.init_pid == process.pid
    assert os2.processes.next_pid == process.pid + 1
    assert os2.processes.processes[process.pid].name == "init"
    assert os2.processes.processes[process.pid].program == b"\x00\x00\x00\x00"
    assert os2.processes.processes[process.pid].address_space.page_table_root == process.address_space.page_table_root
    assert os2.handles[7]["offset"] == 12
    assert os2.desktop.windows[0]["title"] == "saved"


def test_shutdown_marks_machine_off(tmp_path):
    disk = tmp_path / "coreless.img"
    machine = CorelessMachine(8192, storage_path=disk)
    machine.boot()
    machine.shutdown()
    restarted = CorelessMachine(8192, storage_path=disk)
    assert restarted.booted is False
    assert restarted.power_state == "off"


def test_graphics_state_persists_across_restart(tmp_path):
    disk = tmp_path / "coreless.img"
    first = CorelessMachine(8192, storage_path=disk)
    surface = first.graphics.create_surface(4, 2)
    surface.pixels[:8] = b"CORELESS"
    surface.ready = True
    first.graphics.present(surface)
    first.graphics.input({"key": "A"})
    first.graphics.submit({"op": "fill", "value": 7})
    first.boot()
    first.save_state()
    second = CorelessMachine(8192, storage_path=disk)
    assert len(second.graphics.surfaces) == 1
    assert bytes(second.graphics.surfaces[0].pixels[:8]) == b"CORELESS"
    assert second.graphics.scanout is second.graphics.surfaces[0]
    assert second.graphics.input_events == [{"key": "A"}]
    assert second.graphics.commands == [{"op": "fill", "value": 7}]


def test_os_boot_resumes_persistent_machine(tmp_path):
    disk = tmp_path / "coreless.img"
    first = CorelessMachine(8192, storage_path=disk)
    os1 = CorelessOS(first)
    os1.boot()
    first.cpu.r[9] = 0xCAFE
    first.cpu.pc = 0x120
    first.save_state()
    second = CorelessMachine(8192, storage_path=disk)
    assert second.booted is True
    assert second.power_state == "on"
    os2 = CorelessOS(second)
    os2.boot()
    assert second.cpu.r[9] == 0xCAFE
    assert second.cpu.pc == 0x120
    assert second.cpu.csrs[0x01D] == 2


def test_os_shutdown_then_boot_is_cold_start(tmp_path):
    disk = tmp_path / "coreless.img"
    machine = CorelessMachine(8192, storage_path=disk)
    os_runtime = CorelessOS(machine)
    os_runtime.boot()
    machine.shutdown()
    os_runtime.boot()
    assert machine.booted is True
    assert machine.power_state == "on"

def test_complete_checkpoint_restores_machine_image(tmp_path):
    disk = tmp_path / "coreless.img"
    machine = CorelessMachine(64 * 1024, storage_path=disk)
    os_runtime = CorelessOS(machine)
    machine.filesystem.write("/app", b"version-one")
    os_runtime.desktop.open_window("before")
    machine.boot()
    machine.cpu.r[5] = 111
    machine.cpu.memory[4096:4100] = b"SNAP"
    machine.cpu.memory.flush()
    machine.checkpoint("before-change")

    machine.cpu.r[5] = 222
    machine.cpu.memory[4096:4100] = b"EDIT"
    machine.cpu.memory.flush()
    machine.filesystem.write("/app", b"version-two")
    os_runtime.desktop.open_window("after")

    machine.restore_checkpoint("before-change")
    assert machine.cpu.r[5] == 111
    assert bytes(machine.cpu.memory[4096:4100]) == b"SNAP"
    assert machine.filesystem.read("/app") == b"version-one"
    assert [w["title"] for w in os_runtime.desktop.windows] == ["before"]
    assert machine.list_checkpoints() == ["before-change"]


def test_application_and_shell_state_persist(tmp_path):
    disk = tmp_path / "coreless.img"
    machine = CorelessMachine(256 * 1024, storage_path=disk)
    machine.filesystem.write("/init", b"\x00\x00\x00\x00")
    machine.filesystem.write("/app", b"\x00\x00\x00\x00")
    os1 = CorelessOS(machine)
    os1.shell.cwd = "/"
    os1.boot()
    app = os1.processes.create("app", machine.filesystem.read("/app"), parent=os1.init_pid)
    os1.application_state[app.pid] = {
        "path": "/app", "cwd": "/", "argv": ["/app"],
        "state": "ready", "parent": os1.init_pid,
    }
    os1.shell.cwd = "/"
    machine.save_state()

    second = CorelessMachine(256 * 1024, storage_path=disk)
    os2 = CorelessOS(second)
    assert os2.init_pid == 1
    assert os2.application_state[app.pid]["path"] == "/app"


def test_structural_allocations_keep_fixed_shape_during_rewrites(tmp_path):
    from reference.storage import PersistentMachineImage

    disk = tmp_path / "coreless-structure.img"
    image = PersistentMachineImage(disk)
    image.reserve_structure("os/kernel-layout", 16, alignment=8, initial=b"K" * 16)
    image.put("os/kernel-layout", b"N" * 16)
    assert image.get("os/kernel-layout") == b"N" * 16
    try:
        image.put("os/kernel-layout", b"resized")
    except ValueError as exc:
        assert "size is fixed" in str(exc)
    else:
        raise AssertionError("structural allocation was allowed to change size")
    try:
        image.reserve_structure("os/kernel-layout", 32, alignment=8)
    except ValueError as exc:
        assert "shape cannot change" in str(exc)
    else:
        raise AssertionError("structural allocation was allowed to change shape")
    reopened = PersistentMachineImage(disk)
    assert reopened.metadata["structural_allocations"]["os/kernel-layout"] == {
        "size": 16, "alignment": 8,
    }
    assert reopened.get("os/kernel-layout") == b"N" * 16


def test_checkpoint_restore_preserves_structural_allocation_shape():
    from reference.storage import PersistentMachineImage

    image = PersistentMachineImage()
    image.reserve_structure("cpu/component-map", 8, alignment=4, initial=b"CPUCORE!")
    image.create_checkpoint("stable-layout")
    image.put("cpu/component-map", b"NEWCORE!")
    image.restore_checkpoint("stable-layout")
    assert image.get("cpu/component-map") == b"CPUCORE!"
    assert image.metadata["structural_allocations"]["cpu/component-map"]["size"] == 8


def test_checkpoint_cannot_remove_a_structural_allocation():
    from reference.storage import PersistentMachineImage

    image = PersistentMachineImage()
    image.create_checkpoint("before-reservation")
    image.reserve_structure("os/boot-layout", 4)
    try:
        image.restore_checkpoint("before-reservation")
    except ValueError as exc:
        assert "cannot change" in str(exc)
    else:
        raise AssertionError("checkpoint restore removed a protected allocation")


def test_cpu_state_restore_preserves_fixed_architectural_array_allocations():
    machine = CorelessMachine(8192)
    cpu = machine.cpu
    registers = cpu.r
    vector = cpu.vector
    matrix = cpu.matrix
    state = machine._cpu_state(cpu)
    state["r"][1] = 0xCAFE
    machine._restore_cpu_state(cpu, state)
    assert cpu.r is registers
    assert cpu.vector is vector
    assert cpu.matrix is matrix
    assert cpu.r[1] == 0xCAFE


def test_cpu_state_restore_rejects_reshaped_components_without_partial_mutation():
    machine = CorelessMachine(8192)
    cpu = machine.cpu
    before_registers = cpu.r[:]
    state = machine._cpu_state(cpu)
    state["r"][1] = 0xBAD
    state["vector"] = state["vector"][:-1]
    try:
        machine._restore_cpu_state(cpu, state)
    except ValueError as exc:
        assert "structural state shape mismatch" in str(exc)
    else:
        raise AssertionError("CPU state restore accepted a reshaped vector component")
    assert cpu.r == before_registers
