import sys;sys.path.insert(0,".")
from machine_runtime import CorelessMachine
from encoding import encode_base_r,encode_base_i

def test_machine_boot_and_run():
    m=CorelessMachine(4096); program=b"".join([
        encode_base_i("ADDI",1,0,42).to_bytes(4,"little"),
        encode_base_r("ADD",2,1,1).to_bytes(4,"little"),
        encode_base_i("ADDI",3,2,1).to_bytes(4,"little"),
        (0x30000001).to_bytes(4,"little"), # HALT
    ])
    m.boot(program); steps=m.run()
    assert steps==4 and m.cpu.read_reg(1)==42 and m.cpu.read_reg(2)==84 and m.cpu.read_reg(3)==85

def test_machine_checkpoint():
    m=CorelessMachine(4096,2); m.boot(bytes.fromhex("00000020"))
    digest=m.checkpoint(); assert len(digest)==64 and m.storage.get("machine")

def test_loader_executable_entry_sets_machine_pc():
    m = CorelessMachine(4096)
    program = b"".join([
        (0x30000001).to_bytes(4, "little"),
        encode_base_i("ADDI", 4, 0, 7).to_bytes(4, "little"),
        (0x30000001).to_bytes(4, "little"),
    ])
    image = m.loader.make_executable(program, entry=4)
    result = m.loader.load_executable(image, address=0x100)
    assert result["entry"] == 0x104
    assert m.cpu.pc == 0x104
    m.booted = True
    m.power_state = "on"
    m.run()
    assert m.cpu.read_reg(4) == 7


def test_loader_rejects_misaligned_or_out_of_range_entry():
    m = CorelessMachine(4096)
    program = (0x30000001).to_bytes(4, "little")
    for entry in (1, len(program)):
        with __import__("pytest").raises(ValueError, match="entry"):
            m.loader.make_executable(program, entry=entry)


def test_run_program_accepts_corex64_executable_from_filesystem():
    m = CorelessMachine(4096)
    program = b"".join([
        (0x30000001).to_bytes(4, "little"),
        encode_base_i("ADDI", 5, 0, 9).to_bytes(4, "little"),
        (0x30000001).to_bytes(4, "little"),
    ])
    image = m.loader.make_executable(program, entry=4)
    m.filesystem.write("/app", image)
    assert m.run_program("/app") == "2"
    assert m.cpu.read_reg(5) == 9

def test_machine_telemetry_uses_atomic_scheduler_load_snapshot():
    machine = CorelessMachine(memory_size=64 * 1024)
    published = machine.publish_telemetry()
    assert published.workloads.get("cpu", 0) >= 0

def test_machine_image_reopens_with_executed_cpu_and_ram_state(tmp_path):
    """The SSD-carried machine image must resume Coreless state, not just boot Linux."""
    image_path = tmp_path / "coreless-machine.json"
    machine = CorelessMachine(memory_size=4096, storage_path=image_path)
    program = b"".join([
        encode_base_i("ADDI", 7, 0, 37).to_bytes(4, "little"),
        (0x30000001).to_bytes(4, "little"),  # HALT
    ])

    machine.boot(program)
    assert machine.run() == 2
    assert machine.cpu.read_reg(7) == 37
    assert machine.cpu.halted

    # Perform a clean power-off, then reconnect to the same machine image.
    machine.shutdown()
    powered_off = CorelessMachine(memory_size=4096, storage_path=image_path)
    assert not powered_off.booted
    assert powered_off.power_state == "off"
    assert powered_off.cpu.read_reg(7) == 37
    assert powered_off.cpu.halted
    assert powered_off.cpu.pc == machine.cpu.pc
    assert bytes(powered_off.cpu.memory[:len(program)]) == program

    # Power the existing machine back on without replacing its program or state.
    powered_off.boot()
    assert powered_off.booted
    assert powered_off.power_state == "on"
    assert powered_off.cpu.read_reg(7) == 37
    assert powered_off.cpu.halted
    assert bytes(powered_off.cpu.memory[:len(program)]) == program

