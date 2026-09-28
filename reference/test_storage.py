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
    machine.cpus[0].memory[0:4] = b"SHRD"
    machine.cpus[0].memory.flush()
    assert bytes(machine.cpus[1].memory[0:4]) == b"SHRD"


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
