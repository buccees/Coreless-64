import sys
sys.path.insert(0, ".")

from machine_runtime import CorelessMachine
from os_runtime import CorelessOS


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
    assert machine.booted is False
    os_runtime.boot()
    assert machine.booted is True
    assert machine.power_state == "on"
