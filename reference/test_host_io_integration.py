import sys
sys.path.insert(0, ".")

from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities
from host_io import MemoryHostIO, encode_input_event
from host_transport import HostEndpoint, MemoryHostTransportAdapter
from input import (
    CoordinateFrame,
    CorelessInputRouter,
    InputCapabilities,
    InputEvent,
    InputEventType,
    PointingDevice,
    PointingDeviceManager,
)
from system import CorelessSystem


def make_router():
    manager = PointingDeviceManager()
    manager.discover([
        PointingDevice(
            device_id="touch-1",
            name="Host Touch",
            capabilities=InputCapabilities(pointer=True, absolute=True, touch=True),
        )
    ])
    manager.designate("touch-1")
    return CorelessInputRouter(manager)


def make_event(sequence=1):
    return InputEvent(
        abi_version=1,
        event_type=InputEventType.TOUCH_BEGIN,
        device_id="touch-1",
        timestamp_ns=1000 + sequence,
        sequence=sequence,
        coordinate_frame=CoordinateFrame.CORELESS,
        x=10.0,
        y=20.0,
        contact_id=1,
    )


def test_host_io_is_bound_to_persistent_system_and_pumps_all_channels(tmp_path):
    path = tmp_path / "host-io.img"
    system = CorelessSystem(memory_size=4096, storage_path=path)
    system.boot()

    endpoint = HostEndpoint(
        endpoint_id="coreless-io",
        identity=CorelessIdentity("coreless-io"),
        capabilities=HostCapabilities(display=True, input=True, network=True, startup=True),
    )
    io = MemoryHostIO()
    router = make_router()
    interface = CorelessHostInterface(endpoint.identity)
    adapter = MemoryHostTransportAdapter([endpoint])

    negotiated = adapter.connect(
        endpoint,
        interface,
        system=system,
        host_io=io,
        input_router=router,
    )

    assert negotiated == frozenset({"display", "input", "network", "startup"})
    assert interface.host_io is io
    assert interface.system is system

    surface = system.os.desktop.surface
    surface.pixels[:4] = b"ABCD"
    surface.ready = True
    system.os.desktop.present()

    io.input.send_event(encode_input_event(make_event()))
    io.network.send_packet(b"host->coreless")
    outbound = system.machine.network.transmit(b"coreless->host", "host")

    counts = interface.pump_host_io()

    assert counts == {"display": 1, "input": 1, "network_rx": 1, "network_tx": 1}
    assert router.raw_events[0].sequence == 1
    assert system.machine.graphics.poll_input().sequence == 1
    assert system.machine.network.poll_rx() is not None
    assert io.display.receive_frame()[:4] == b"ABCD"
    assert io.network.receive_packet() == outbound.data
