import sys;sys.path.insert(0,".")
from machine import InterruptController,DeviceFabric,Device,DMAController,DMAError
def test_interrupt_priority_and_ipi():
    ic=InterruptController(2);ic.route(10,1,5);ic.route(3,1,20);e=ic.claim(1);assert e.source==3;assert ic.send_ipi(0,1,7);assert ic.cpus[1].pending_ipi&(1<<7)
def test_cpu_hotplug():
    ic=InterruptController(1);ic.add_cpu(1);assert ic.cpus[1].online;ic.remove_cpu(1);assert not ic.route(1,1)
def test_dma_domains():
    d=DMAController();d.map(4,0x1000,0x1000);assert d.check(4,0x1800,0x100)
    try:d.check(4,0x1F00,0x200);assert False
    except DMAError:pass
def test_device_discovery():
    f=DeviceFabric();i=f.add(Device(1,capabilities=3,resource_base=0x8000,resource_length=0x100));assert f.discover()[i].device_type==1
