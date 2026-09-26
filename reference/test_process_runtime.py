import sys
sys.path.insert(0, ".")
from app import hello_program
from machine_runtime import CorelessMachine
from process import ProcessManager
from loader import ProgramLoader

def test_scheduler_and_process_metadata():
    machine = CorelessMachine(4096, 1)
    pm = ProcessManager(machine)
    p = pm.create("hello", hello_program(), parent=7)
    assert p.pid == 1
    result = pm.start(p.pid)
    assert result.state == "exited"
    assert result.ticks > 0
    assert pm.wait(7).pid == 1

def test_corex64_executable_round_trip():
    machine = CorelessMachine(4096, 1)
    loader = ProgramLoader(machine)
    image = loader.make_executable(hello_program())
    result = loader.load_executable(image)
    assert result["entry"] == 0
    assert result["size"] == len(hello_program())
