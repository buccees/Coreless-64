import sys
sys.path.insert(0, ".")
from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities
from host_transport import HostEndpoint, MemoryHostTransportAdapter
from system import CorelessSystem
from device_command import DeviceCommand, OP_STATUS


def test_host_transport_binds_persistent_system_at_connect(tmp_path):
    image = tmp_path / "coreless.json"
    system = CorelessSystem(memory_size=128 * 1024, storage_path=image)
    endpoint = HostEndpoint(
        "coreless-persistent-host",
        CorelessIdentity("coreless-persistent-host"),
        HostCapabilities(display=True, startup=True),
        device_capabilities={"display", "startup"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-persistent-host"))

    negotiated = adapter.connect(endpoint, interface, system=system)

    assert negotiated == frozenset({"display", "startup"})
    assert interface.status()["attached"]
    reply = adapter.send_command(endpoint, interface, DeviceCommand(OP_STATUS, 901))
    assert b"attached" in reply.payload

    system.command("write /host-bound persisted")
    adapter.disconnect(interface)

    reopened = CorelessSystem(memory_size=128 * 1024, storage_path=image)
    reopened.boot()
    assert reopened.command("cat /host-bound") == "persisted"


def test_host_transport_session_can_bind_system_once(tmp_path):
    image = tmp_path / "session.json"
    system = CorelessSystem(memory_size=128 * 1024, storage_path=image)
    endpoint = HostEndpoint(
        "coreless-session-system",
        CorelessIdentity("coreless-session-system"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-session-system"))

    session = adapter.open_session(endpoint, interface, system=system)
    assert session.attached
    assert interface._system is system
