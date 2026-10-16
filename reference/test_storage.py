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


def test_machine_image_sync_fsyncs_directory_after_atomic_replace(monkeypatch, tmp_path):
    import storage as storage_module

    disk = tmp_path / "durable.img"
    image = storage_module.PersistentMachineImage(disk)
    events = []
    original_fsync = storage_module.os.fsync
    original_replace = storage_module.os.replace

    def record_fsync(fd):
        events.append(("fsync", os.fstat(fd).st_mode))
        return original_fsync(fd)

    def record_replace(source, destination):
        events.append(("replace", str(destination)))
        return original_replace(source, destination)

    import os
    monkeypatch.setattr(storage_module.os, "fsync", record_fsync)
    monkeypatch.setattr(storage_module.os, "replace", record_replace)
    image.put("durability/probe", b"persisted")

    replace_index = next(i for i, event in enumerate(events) if event[0] == "replace")
    fsync_indices = [i for i, event in enumerate(events) if event[0] == "fsync"]
    assert len(fsync_indices) == 2
    assert fsync_indices[0] < replace_index < fsync_indices[1]
    reopened = storage_module.PersistentMachineImage(disk)
    assert reopened.get("durability/probe") == b"persisted"


import pytest


@pytest.mark.parametrize(
    ("failure_stage", "expected_value"),
    [
        ("file_fsync", b"old"),
        ("replace", b"old"),
        # Directory fsync happens after replace, so the new complete image is
        # visible even though durability confirmation fails.
        ("directory_fsync", b"new"),
    ],
)
def test_machine_image_sync_failures_leave_a_reopenable_image(
    monkeypatch, tmp_path, failure_stage, expected_value
):
    import os
    import storage as storage_module

    disk = tmp_path / "failure-stage.img"
    image = storage_module.PersistentMachineImage(disk)
    image.put("durability/value", b"old")
    original_fsync = storage_module.os.fsync
    original_replace = storage_module.os.replace
    fsync_calls = 0

    def injected_fsync(fd):
        nonlocal fsync_calls
        fsync_calls += 1
        target_call = 1 if failure_stage == "file_fsync" else 2
        if failure_stage in ("file_fsync", "directory_fsync") and fsync_calls == target_call:
            raise OSError(f"injected {failure_stage} failure")
        return original_fsync(fd)

    def injected_replace(source, destination):
        if failure_stage == "replace":
            raise OSError("injected replace failure")
        return original_replace(source, destination)

    monkeypatch.setattr(storage_module.os, "fsync", injected_fsync)
    monkeypatch.setattr(storage_module.os, "replace", injected_replace)
    with pytest.raises(OSError, match=f"injected {failure_stage} failure"):
        image.put("durability/value", b"new")

    reopened = storage_module.PersistentMachineImage(disk)
    assert reopened.get("durability/value") == expected_value


def test_large_sparse_machine_image_reopens_and_resumes_state(tmp_path):
    disk = tmp_path / "large-coreless.img"
    memory_size = 16 * 1024 * 1024
    first = CorelessMachine(memory_size, storage_path=disk)
    first.boot()

    # Touch the first and final RAM pages without materializing the whole RAM.
    first.cpu.memory[0:4] = b"BOOT"
    first.cpu.memory[memory_size - 4:memory_size] = b"TAIL"
    first.cpu.memory.flush()
    first.cpu.r[12] = 0xC064
    first.cpu.pc = memory_size - 4
    first.save_state()

    reopened = CorelessMachine(memory_size, storage_path=disk)
    assert reopened.booted is True
    assert reopened.cpu.memory.size == memory_size
    assert bytes(reopened.cpu.memory[0:4]) == b"BOOT"
    assert bytes(reopened.cpu.memory[memory_size - 4:memory_size]) == b"TAIL"
    assert reopened.cpu.r[12] == 0xC064
    assert reopened.cpu.pc == memory_size - 4
    assert sum(name.startswith("ram/ram/") for name in reopened.storage.objects) == 2


def test_reopen_rejects_ram_size_mismatch(tmp_path):
    disk = tmp_path / "ram-size-mismatch.img"
    machine = CorelessMachine(16 * 1024 * 1024, storage_path=disk)
    machine.cpu.memory[0:4] = b"BOOT"
    machine.cpu.memory.flush()

    with pytest.raises(ValueError, match="RAM size does not match machine image"):
        CorelessMachine(8 * 1024 * 1024, storage_path=disk)


def test_storage_region_policy_rejects_cross_region_name_collisions():
    from storage import StorageRegionPolicy

    policy = StorageRegionPolicy()
    policy.register_region("model", ("model/",), mutable=False)
    policy.register_region("state", ("state/",), mutable=True)

    assert policy.region_for("model/qwen3/weights.bin") == "model"
    assert policy.region_for("state/session-1") == "state"
    with pytest.raises(PermissionError, match="immutable"):
        policy.validate_write("model/qwen3/weights.bin")
    policy.validate_write("state/session-1")
    with pytest.raises(ValueError, match="overlap"):
        policy.register_region("overlap", ("model/", "state/"), mutable=True)


def test_storage_region_policy_rejects_unclassified_objects():
    from storage import StorageRegionPolicy

    policy = StorageRegionPolicy()
    policy.register_region("config", ("config/",), mutable=True)
    with pytest.raises(ValueError, match="no registered storage region"):
        policy.region_for("random/unclassified")
