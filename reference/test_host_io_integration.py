import sys
sys.path.insert(0, ".")

import pytest

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



def test_host_io_rejects_nonconforming_bundle():
    from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities

    interface = CorelessHostInterface(CorelessIdentity("invalid-bundle"))
    interface.attach(
        CorelessIdentity("invalid-bundle"),
        HostCapabilities(display=True, input=True, network=True, startup=True),
    )
    try:
        interface.bind_host_io(object())
    except TypeError:
        pass
    else:
        raise AssertionError("nonconforming host I/O bundle was accepted")



def test_host_io_pump_propagates_transport_failures():
    endpoint_identity = CorelessIdentity("broken-input")
    interface = CorelessHostInterface(endpoint_identity)
    interface.attach(endpoint_identity, HostCapabilities(input=True))
    io = MemoryHostIO()
    interface.bind_host_io(io, input_router=make_router())

    def disconnected():
        raise RuntimeError("input transport disconnected")

    io.input.receive_event = disconnected
    with pytest.raises(RuntimeError, match="input transport disconnected"):
        interface.pump_host_io()


def test_host_io_pump_preserves_outbound_packet_when_transport_send_fails(tmp_path):
    system = CorelessSystem(memory_size=4096, storage_path=tmp_path / "host-io-failure.img")
    system.boot()
    identity = CorelessIdentity("outbound-failure")
    interface = CorelessHostInterface(identity)
    interface.attach(identity, HostCapabilities(network=True))
    io = MemoryHostIO()
    interface.bind_host_io(io)
    outbound = system.machine.network.transmit(b"retry-me", "host")

    def disconnected(packet):
        raise RuntimeError("network transport disconnected")

    io.network.send_packet = disconnected
    with pytest.raises(RuntimeError, match="network transport disconnected"):
        interface.pump_host_io()

    assert system.machine.network.tx == [outbound]

    # Once the transport recovers, the same queued packet is delivered and
    # only then removed from the Coreless transmit queue.
    io.network.send_packet = lambda packet: io.network.packets.append(bytes(packet))
    counts = interface.pump_host_io()
    assert counts["network_tx"] == 1
    assert io.network.receive_packet() == b"retry-me"
    assert system.machine.network.tx == []
