import sys
sys.path.insert(0,".")
from machine_runtime import CorelessMachine

def test_virtual_ram_persists_across_machine_restart(tmp_path):
    disk=tmp_path/"coreless.img"
    first=CorelessMachine(8192,storage_path=disk)
    first.boot()
    first.cpu.memory[4096:4100]=b"CL64"
    first.cpu.memory.flush()
    second=CorelessMachine(8192,storage_path=disk)
    assert bytes(second.cpu.memory[4096:4100])==b"CL64"
    assert second.cpu.memory.size==8192

def test_virtual_ram_is_sparse(tmp_path):
    disk=tmp_path/"coreless.img"
    machine=CorelessMachine(64*1024,storage_path=disk)
    assert not any(k.startswith("ram/ram0/") for k in machine.storage.objects)
    machine.cpu.memory[0:4]=b"BOOT"
    machine.cpu.memory.flush()
    assert "ram/ram0/0" in machine.storage.objects
    assert len(machine.storage.objects["ram/ram0/0"])==4096
