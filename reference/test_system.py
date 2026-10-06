import sys
sys.path.insert(0, ".")

from app import hello_program
from machine_runtime import CorelessMachine
from system import CorelessSystem


def test_complete_system_boot_and_run(tmp_path):
    image = tmp_path / "coreless.json"
    system = CorelessSystem(
        memory_size=256 * 1024,
        storage_path=image,
    )
    system.machine.filesystem.write("/init", hello_program())

    system.boot()
    assert system.machine.booted
    assert system.machine.power_state == "on"
    assert system.status()["system_version"] == 1
    assert system.boot_manifest["init"] == "/init"

    steps = system.run()
    assert steps > 0
    assert system.os.init_pid in system.os.processes.processes
    assert system.os.processes.processes[system.os.init_pid].state == "exited"
    assert image.exists()


def test_complete_system_resumes_persistent_state(tmp_path):
    image = tmp_path / "coreless.json"
    first = CorelessSystem(memory_size=256 * 1024, storage_path=image)
    first.machine.filesystem.write("/init", hello_program())
    first.boot()
    first.run()
    first.machine.filesystem.write("/persist", b"coreless-state")
    first.checkpoint("before-reboot")
    first.shutdown()

    second = CorelessSystem(memory_size=256 * 1024, storage_path=image)
    assert second.machine.booted is False
    assert second.machine.filesystem.read("/persist") == b"coreless-state"
    second.boot()
    assert second.machine.booted
    assert second.boot_manifest["os_version"] == second.os.VERSION


def test_complete_system_shell_uses_native_os(tmp_path):
    system = CorelessSystem(memory_size=128 * 1024, storage_path=tmp_path / "coreless.json")
    system.machine.filesystem.write("/init", hello_program())
    system.boot()
    assert system.command("pwd") == "/"
    assert "Coreless-64" in system.command("status")
    system.command("write /message hello")
    assert system.command("cat /message") == "hello"


def test_system_boot_accepts_corex64_init_entry(tmp_path):
    system = CorelessSystem(memory_size=256 * 1024, storage_path=tmp_path / "coreless.json")
    program = b"".join([
        (0x30000001).to_bytes(4, "little"),
        (0x30000001).to_bytes(4, "little"),
    ])
    image = system.os.processes.machine.loader.make_executable(program, entry=4)
    system.machine.filesystem.write("/init", image)
    system.boot()
    process = system.os.processes.processes[system.os.init_pid]
    assert process.program == program
    assert process.pc == process.address_space.code_base + 4
