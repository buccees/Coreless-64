import sys
sys.path.insert(0, ".")
from app import hello_program
from machine_runtime import CorelessMachine
from os_runtime import CorelessOS

def test_native_shell_commands_end_to_end():
    os = CorelessOS(CorelessMachine(4096, 2)).run()
    assert os.command("status").startswith("Coreless-64")
    assert os.command("cpu").startswith("Coreless-64 CPUs=2")
    assert os.command("memory") == "memory=4096 bytes"
    os.command('write /hello "hello-coreless"')
    assert os.command("cat /hello") == "hello-coreless"
    assert "/hello" in os.command("ls").splitlines()
    os.command("write /hello-app " + hello_program().hex())
    assert os.command("cat /hello-app") == hello_program().hex()
    assert "PID STATE NAME PC" in os.command("ps")
    assert "pid=1" in os.command("run /hello-app")
    assert "exited" in os.command("ps")
    os.network.device.configure(link_up=True)
    assert os.command("net ping 192.0.2.1") == "PING sent to 192.0.2.1"
    assert "link=up" in os.command("net")
    assert "window opened" in os.command("open Test 100 80")
    assert "Test" in os.command("windows")
    assert "display=640x480" in os.command("desktop")
    assert os.command("checkpoint shell-test") == "checkpoint saved: shell-test"
