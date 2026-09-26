"""Integrated Coreless-64 reference machine runtime."""
from core import CorelessCPU
from machine import InterruptController,DeviceFabric
from storage import PersistentMachineImage
from io import NetworkDevice,GraphicsDevice
from filesystem import FileSystem
from loader import ProgramLoader

class CorelessMachine:
    def __init__(self,memory_size=1<<20,cpu_count=1):
        if cpu_count<1: raise ValueError("cpu_count must be positive")
        self.cpus=[CorelessCPU(memory_size) for _ in range(cpu_count)]
        for i,cpu in enumerate(self.cpus):
            cpu.csrs[0x00A]=i; cpu.csrs[0x00B]=cpu_count
        self.interrupts=InterruptController(cpu_count)
        self.devices=DeviceFabric(); self.devices.attach_interrupt_controller(self.interrupts)
        self.storage=PersistentMachineImage()
        self.network=NetworkDevice(); self.graphics=GraphicsDevice()
        self.filesystem=FileSystem(self.storage)
        self.loader=ProgramLoader(self)
        self.booted=False
    @property
    def cpu(self): return self.cpus[0]
    def load_program(self,program,address=0):
        end=address+len(program)
        if address<0 or end>len(self.cpu.memory): raise ValueError("program outside memory")
        self.cpu.memory[address:end]=program; self.cpu.pc=address
    def boot(self,program=None,address=0):
        if program is not None: self.load_program(program,address)
        self.booted=True
        return self.cpu
    def step(self,cpu_id=0):
        if not self.booted: raise RuntimeError("machine not booted")
        return self.cpus[cpu_id].step()
    def run(self,max_steps=100000,cpu_id=0):
        if not self.booted: raise RuntimeError("machine not booted")
        steps=0
        while steps<max_steps and not self.cpus[cpu_id].halted:
            self.cpus[cpu_id].step(); steps+=1
        return steps
    def run_program(self,path):
        program=self.filesystem.read(path)
        self.loader.load(program,0)
        self.booted=True
        return str(self.run())

    def checkpoint(self,name="machine"):
        state={"booted":self.booted,"cpus":[]}
        for c in self.cpus:
            state["cpus"].append({"r":c.r[:],"pc":c.pc,"sp":c.sp,"privilege":c.privilege,
                                  "halted":c.halted,"cycle":c.cycle,"instret":c.instret})
        return self.storage.checkpoint(name,state)
