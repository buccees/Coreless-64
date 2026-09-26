"""Hardware-shaped Coreless machine fabric reference model."""
from dataclasses import dataclass
@dataclass
class CPUContext:
    cpu_id:int
    online:bool=True
    halted:bool=False
    pending_ipi:int=0
@dataclass
class IRQ:
    source:int
    priority:int
    target:int
    code:int=2
class InterruptController:
    def __init__(self,cpu_count=1):
        self.cpus={i:CPUContext(i) for i in range(cpu_count)}; self.pending={i:[] for i in self.cpus}
    def add_cpu(self,cpu_id): self.cpus[cpu_id]=CPUContext(cpu_id); self.pending[cpu_id]=[]
    def remove_cpu(self,cpu_id):
        if cpu_id in self.cpus: self.cpus[cpu_id].online=False
    def route(self,source,target,priority=0,code=2):
        if target not in self.cpus or not self.cpus[target].online:return False
        self.pending[target].append(IRQ(source,priority,target,code)); self.pending[target].sort(key=lambda x:(-x.priority,x.source)); return True
    def send_ipi(self,source_cpu,target_cpu,vector=0):
        if not self.route(source_cpu,target_cpu,255,3):return False
        self.cpus[target_cpu].pending_ipi|=1<<vector; return True
    def claim(self,cpu_id):
        q=self.pending.get(cpu_id,[]); return q.pop(0) if q else None
class DMAError(Exception):pass
@dataclass
class DMARegion: base:int; length:int; writable:bool=True
class DMAController:
    def __init__(self):self.domains={}
    def map(self,domain,base,length,writable=True):
        if base<0 or length<=0:raise DMAError("invalid DMA region")
        self.domains.setdefault(domain,[]).append(DMARegion(base,length,writable))
    def check(self,domain,addr,length,write=False):
        for r in self.domains.get(domain,[]):
            if r.base<=addr and addr+length<=r.base+r.length:
                if write and not r.writable:raise DMAError("DMA write protection")
                return True
        raise DMAError("DMA protection fault")
@dataclass
class Device:
    device_type:int; version:int=1; capabilities:int=0; resource_base:int=0; resource_length:int=0
    interrupt_base:int=0; interrupt_count:int=0; dma_domain:int=0; command_interface:int=0; extension_pointer:int=0
class DeviceFabric:
    def __init__(self):self.devices=[]; self.dma=DMAController(); self.interrupts=None
    def attach_interrupt_controller(self,ic):self.interrupts=ic
    def add(self,device):self.devices.append(device); return len(self.devices)-1
    def discover(self):return list(self.devices)
