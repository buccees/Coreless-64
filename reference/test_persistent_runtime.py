import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from system import CorelessSystem


def test_persistent_runtime_resume_and_command(tmp_path):
    image = tmp_path / "coreless.json"

    first = CorelessSystem(memory_size=128 * 1024, storage_path=image)
    first.command("write /persistent hello")
    first.machine.cpu.r[6] = 0xCAFE
    first.machine.save_state()

    second = CorelessSystem(memory_size=128 * 1024, storage_path=image)
    second.boot()
    assert second.command("cat /persistent") == "hello"
    assert second.machine.cpu.r[6] == 0xCAFE


def test_persistent_runtime_shutdown_survives_reopen(tmp_path):
    image = tmp_path / "coreless.json"

    system = CorelessSystem(memory_size=128 * 1024, storage_path=image)
    system.boot()
    system.shutdown()

    reopened = CorelessSystem(memory_size=128 * 1024, storage_path=image)
    assert reopened.machine.booted is False
    assert reopened.machine.power_state == "off"
