"""Coreless virtual-machine reference model."""
from dataclasses import dataclass, field

@dataclass
class VCPU:
    vcpu_id:int
    registers:list=field(default_factory=lambda:[0]*32)
    pc:int=0
    sp:int=0
    privilege:int=0
    halted:bool=False

@dataclass
class VM:
    vmid:int
    memory_size:int
    vcpus:list=field(default_factory=list)
    pending_interrupts:list=field(default_factory=list)
    devices:list=field(default_factory=list)
    running:bool=False

class Hypervisor:
    def __init__(self,cpu_count=1):
        self.cpu_count=cpu_count; self.vms={}; self.next_vmid=1
    def create_vm(self,memory_size,vcpus=1):
        if vcpus<1 or vcpus>self.cpu_count: raise ValueError("invalid vCPU allocation")
        vm=VM(self.next_vmid,memory_size,[VCPU(i) for i in range(vcpus)])
        self.vms[vm.vmid]=vm; self.next_vmid+=1; return vm
    def destroy_vm(self,vmid):
        self.vms.pop(vmid,None)
    def inject_interrupt(self,vmid,vector):
        vm=self.vms[vmid]; vm.pending_interrupts.append(vector)
    def run(self,vmid):
        vm=self.vms[vmid]; vm.running=True; return vm
    def stop(self,vmid):
        vm=self.vms[vmid]; vm.running=False
    def snapshot(self,vmid):
        vm=self.vms[vmid]
        return {"vmid":vm.vmid,"memory_size":vm.memory_size,"running":vm.running,
                "vcpus":[{"id":v.vcpu_id,"registers":v.registers[:],"pc":v.pc,"sp":v.sp,"privilege":v.privilege,"halted":v.halted} for v in vm.vcpus],
                "pending_interrupts":list(vm.pending_interrupts),"devices":list(vm.devices)}
