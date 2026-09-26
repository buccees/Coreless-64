"""Minimal Coreless firmware/boot contract for the reference machine."""
class BootError(Exception): pass

class Firmware:
    MAGIC=b"CORELESS64"
    VERSION=1
    def __init__(self,machine):
        self.machine=machine
        self.status={"memory":False,"interrupts":False,"devices":False,"boot":False}
    def initialize(self):
        if not self.machine.cpus: raise BootError("no execution context")
        self.status["memory"]=True
        self.status["interrupts"]=True
        self.status["devices"]=True
        for cpu in self.machine.cpus:
            cpu.csrs[0x01D]=1
        return True
    def boot(self,program,address=0):
        if not all(self.status[k] for k in ("memory","interrupts","devices")):
            self.initialize()
        self.machine.boot(program,address)
        self.status["boot"]=True
        for cpu in self.machine.cpus:
            cpu.csrs[0x01D]=2
        return self.machine.cpu
