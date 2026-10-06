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


def test_complete_system_owns_persistent_local_ai_runtime(tmp_path):
    from ai.interfaces import AIResult

    system = CorelessSystem(
        memory_size=128 * 1024,
        storage_path=tmp_path / "coreless-ai.json",
    )
    assert system.ai.registry.enabled_cores() == (
        "qwen3", "deepseek", "gpt-oss", "gemma", "codestral"
    )
    request = system.ai.request("inspect the machine")
    assert request.request_id == "default:request:1"
    system.ai.session.record_result(AIResult(request.request_id, "qwen3", "analysis"))
    system.checkpoint("ai-state")

    resumed = CorelessSystem(
        memory_size=128 * 1024,
        storage_path=tmp_path / "coreless-ai.json",
    )
    assert resumed.ai.session.session_id == "default"
    assert len(resumed.ai.session.events()) == 2
    assert resumed.ai.status()["event_count"] == 2


def test_complete_system_can_persist_ai_runtime_without_network(tmp_path):
    system = CorelessSystem(
        memory_size=128 * 1024,
        storage_path=tmp_path / "coreless-ai.json",
    )
    system.ai.save()
    assert system.machine.storage.get("ai/registry")
    assert system.machine.storage.get("ai/session/default")


def test_complete_system_registers_persistent_ai_as_machine_resources(tmp_path):
    system = CorelessSystem(
        memory_size=128 * 1024,
        storage_path=tmp_path / "coreless-ai-resources.json",
    )
    resources = system.status()["ai"]["machine_resources"]
    assert resources == (
        "ai:codestral",
        "ai:deepseek",
        "ai:gemma",
        "ai:gpt-oss",
        "ai:qwen3",
    )
    assert system.machine.scheduler.load("ai:qwen3") == 0


def test_ai_work_submission_contract_is_machine_owned(tmp_path):
    system = CorelessSystem(
        memory_size=128 * 1024,
        storage_path=tmp_path / "coreless-ai-resources.json",
    )
    request = system.ai.request("inspect")
    assert request.authority.value == "recommend"
    assert "ai:qwen3" in system.machine.scheduler.resources()
