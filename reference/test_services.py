import sys;sys.path.insert(0,".")
from machine_runtime import CorelessMachine
from process import ProcessManager
from netstack import NetworkStack
from display import Desktop
from app import hello_program
def test_process_manager():
    m=CorelessMachine(256 * 1024); pm=ProcessManager(m); p=pm.create("hello",hello_program()); pm.start(p.pid)
    assert p.state=="exited" and p.registers[1]==42 and p.registers[2]==84
def test_network_service():
    m=CorelessMachine(); m.network.configure(True); n=NetworkStack(m.network); n.configure(ipv4="192.0.2.2")
    p=n.ping_frame("192.0.2.1"); assert p.data.startswith(b"PING")
def test_desktop_service():
    m=CorelessMachine(); d=Desktop(m.graphics); w=d.open_window("Coreless",100,100); d.present()
    assert w["title"]=="Coreless" and m.graphics.scanout is d.surface
