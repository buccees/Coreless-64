import sys
sys.path.insert(0, ".")

from device_command import OP_CAPABILITIES, OP_EXECUTE, OP_STATUS, OP_SYNC, DeviceCommand, is_error
from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities


def test_host_interface_dispatches_capabilities_command():
    interface = CorelessHostInterface(CorelessIdentity("coreless-cmd"))
    interface.attach(interface.discover(), HostCapabilities(display=True, input=True))
    reply = interface.handle_command(DeviceCommand(OP_CAPABILITIES, 1))
    assert not is_error(reply)
    assert reply.request_id == 1
    assert reply.payload == b"display|input"


def test_host_interface_dispatches_status_and_sync():
    interface = CorelessHostInterface(CorelessIdentity("coreless-cmd"))
    interface.attach(interface.discover(), HostCapabilities(display=True))
    status = interface.handle_command(DeviceCommand(OP_STATUS, 2))
    sync = interface.handle_command(DeviceCommand(OP_SYNC, 3))
    assert not is_error(status)
    assert b"coreless-cmd" in status.payload
    assert sync.payload == b"ok"


def test_host_interface_exposes_execution_endpoint_only_when_bound():
    interface = CorelessHostInterface(CorelessIdentity("coreless-cmd"), supported={"compute"})
    interface.attach(interface.discover(), HostCapabilities())
    reply = interface.handle_command(DeviceCommand(OP_EXECUTE, 4))
    assert is_error(reply)
    assert b"no Coreless system" in reply.payload
