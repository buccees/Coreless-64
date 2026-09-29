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
    inbox:list=field(default_factory=list)

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
        self._next_capability=1; self._ipc_caps={}; self._shared_regions={}
    def create_vm(self,memory_size,vcpus=1):
        if vcpus<1 or vcpus>self.cpu_count: raise ValueError("invalid vCPU allocation")
        vm=VM(self.next_vmid,memory_size,[VCPU(i) for i in range(vcpus)])
        self.vms[vm.vmid]=vm; self.next_vmid+=1; return vm
    def destroy_vm(self,vmid):
        if vmid not in self.vms:
            return
        self.vms.pop(vmid,None)
        self._ipc_caps = {
            cap: pair for cap, pair in self._ipc_caps.items()
            if vmid not in pair
        }
        self._shared_regions = {
            key: perms for key, perms in self._shared_regions.items()
            if vmid not in key[:2]
        }
    def inject_interrupt(self,vmid,vector):
        vm=self.vms[vmid]; vm.pending_interrupts.append(vector)
    def run(self,vmid):
        vm=self.vms[vmid]
        if not vm.vcpus:
            raise ValueError("VM has no vCPUs")
        vm.running=True
        return vm
    def stop(self,vmid):
        vm=self.vms[vmid]; vm.running=False
    def set_vcpu_state(self, vmid, vcpu_id, *, registers=None, pc=None, sp=None,
                       privilege=None, halted=None):
        v = self._vcpu(vmid, vcpu_id)
        if registers is not None:
            if len(registers) != 32:
                raise ValueError("vCPU requires 32 registers")
            v.registers = [int(x) & ((1 << 64) - 1) for x in registers]
            v.registers[0] = 0
        if pc is not None: v.pc = int(pc) & ((1 << 64) - 1)
        if sp is not None: v.sp = int(sp) & ((1 << 64) - 1)
        if privilege is not None:
            if privilege not in (0, 1, 2, 3): raise ValueError("invalid privilege")
            v.privilege = privilege
        if halted is not None: v.halted = bool(halted)
    def snapshot_vcpu(self, vmid, vcpu_id):
        v = self._vcpu(vmid, vcpu_id)
        return {"id": v.vcpu_id, "registers": v.registers[:], "pc": v.pc,
                "sp": v.sp, "privilege": v.privilege, "halted": v.halted,
                "inbox": list(v.inbox)}
    def restore_vcpu(self, vmid, vcpu_id, state):
        self._vcpu(vmid, vcpu_id)
        required = {"registers", "pc", "sp", "privilege", "halted", "inbox"}
        if not required.issubset(state):
            raise ValueError("incomplete vCPU state")
        self.set_vcpu_state(vmid, vcpu_id, registers=state["registers"],
                            pc=state["pc"], sp=state["sp"],
                            privilege=state["privilege"], halted=state["halted"])
        self._vcpu(vmid, vcpu_id).inbox = list(state["inbox"])
    def _vcpu(self, vmid, vcpu_id):
        vm=self.vms[vmid]
        if not 0 <= vcpu_id < len(vm.vcpus): raise ValueError("invalid vCPU")
        return vm.vcpus[vcpu_id]
    def grant_ipc(self, source_vmid, target_vmid):
        if source_vmid not in self.vms or target_vmid not in self.vms: raise ValueError("unknown VM")
        cap=self._next_capability; self._next_capability+=1
        self._ipc_caps[cap]=(source_vmid,target_vmid); return cap
    def revoke_ipc(self, capability): self._ipc_caps.pop(capability,None)
    def send_message(self, source_vmid, source_vcpu, target_vmid, target_vcpu, payload, capability=None):
        self._vcpu(source_vmid,source_vcpu)
        target=self._vcpu(target_vmid,target_vcpu)
        if source_vmid != target_vmid and self._ipc_caps.get(capability) != (source_vmid,target_vmid):
            raise PermissionError("VM-to-VM IPC capability required")
        if not isinstance(payload,(bytes,bytearray,memoryview)): raise TypeError("IPC payload must be bytes-like")
        target.inbox.append(bytes(payload))
    def recv_message(self, vmid, vcpu_id):
        v=self._vcpu(vmid,vcpu_id); return v.inbox.pop(0) if v.inbox else None
    def share_memory(self, owner_vmid, target_vmid, region_id, permissions):
        if owner_vmid not in self.vms or target_vmid not in self.vms: raise ValueError("unknown VM")
        if permissions not in (1,2,3): raise ValueError("invalid sharing permissions")
        self._shared_regions[(owner_vmid,target_vmid,region_id)]=permissions
    def revoke_shared_memory(self, owner_vmid, target_vmid, region_id):
        self._shared_regions.pop((owner_vmid,target_vmid,region_id),None)
    def check_shared_memory(self, accessor_vmid, owner_vmid, target_vmid, region_id, write=False):
        if accessor_vmid == owner_vmid: return True
        permissions=self._shared_regions.get((owner_vmid,target_vmid,region_id),0)
        required=2 if write else 1
        if not permissions & required: raise PermissionError("shared-memory permission required")
        return True
    def snapshot(self,vmid):
        vm=self.vms[vmid]
        return {"vmid":vm.vmid,"memory_size":vm.memory_size,"running":vm.running,
                "vcpus":[{"id":v.vcpu_id,"registers":v.registers[:],"pc":v.pc,"sp":v.sp,"privilege":v.privilege,"halted":v.halted, "inbox":list(v.inbox)} for v in vm.vcpus],
                "pending_interrupts":list(vm.pending_interrupts),"devices":list(vm.devices)}
