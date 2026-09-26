import sys;sys.path.insert(0,".")
from virtualization import Hypervisor
def test_vm_lifecycle_and_interrupt():
    h=Hypervisor(4); vm=h.create_vm(1<<20,2); h.inject_interrupt(vm.vmid,7); h.run(vm.vmid)
    snap=h.snapshot(vm.vmid)
    assert vm.running and snap["vcpus"][1]["pc"]==0 and snap["pending_interrupts"]==[7]
    h.stop(vm.vmid); h.destroy_vm(vm.vmid); assert vm.vmid not in h.vms
