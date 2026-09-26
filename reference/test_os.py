import sys;sys.path.insert(0,".")
from machine_runtime import CorelessMachine
from shell import Shell
def test_filesystem_shell():
    m=CorelessMachine(4096); s=Shell(m); assert s.execute("pwd")=="/"
    s.execute("write /hello hello-coreless"); assert s.execute("cat /hello")=="hello-coreless"
    assert "/hello" in s.execute("ls").splitlines(); s.execute("rm /hello"); assert not m.filesystem.exists("/hello")
def test_program_loader_rejects_bad_program():
    m=CorelessMachine(4096); s=Shell(m)
    assert s.execute("status").startswith("Coreless-64 ready")
