import sys;sys.path.insert(0,".")
from machine_runtime import CorelessMachine
from firmware import Firmware
def test_firmware_boot():
    m=CorelessMachine(4096); f=Firmware(m); f.initialize()
    f.boot(bytes.fromhex("00000020"))
    assert f.status["boot"] and m.booted and m.cpu.csrs[0x01D]==2
