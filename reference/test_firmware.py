import sys;sys.path.insert(0,".")
from machine_runtime import CorelessMachine
from firmware import Firmware
def test_firmware_boot():
    m=CorelessMachine(4096); f=Firmware(m); f.initialize()
    f.boot((0x30000001).to_bytes(4,"little"))
    assert f.status["boot"] and m.booted and m.cpu.csrs[0x01D]==2
