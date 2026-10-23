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



def test_arduino_input_flows_through_host_abi_with_optional_vigil(tmp_path):
    from arduino_io import ArduinoInputAdapter, ArduinoSerialIO, encode_message
    from host_io import MemoryInputTransport
    from input import InterpretedInputEvent

    class FakeSerial:
        def __init__(self, reads):
            self.reads = list(reads)

        def write(self, data):
            return len(data)

        def readline(self):
            if not self.reads:
                return b""
            return self.reads.pop(0)

    class FakeVigil:
        def __init__(self):
            self.seen = []

        def available(self):
            return True

        def interpret(self, event, device):
            self.seen.append((event, device.device_id))
            return (InterpretedInputEvent(
                interpretation_id=f"vigil-{event.sequence}",
                kind="pointer_move",
                device_id=event.device_id,
                timestamp_ns=event.timestamp_ns,
                source_sequence=(event.sequence,),
                metadata={"source": "test-vigil", "raw_sequence": event.sequence},
            ),)

    serial = FakeSerial([
        encode_message("event", "arduino-1", 20, {
            "event_type": "pointer_move", "x": 12.5, "y": 7,
        }),
        encode_message("event", "arduino-1", 21, {
            "event_type": "pointer_move", "x": 14, "y": 9,
        }),
    ])
    device = PointingDevice(
        device_id="arduino-1",
        name="Arduino pointing source",
        capabilities=InputCapabilities(pointer=True, absolute=True),
        host_identity="arduino:serial",
    )
    manager = PointingDeviceManager()
    manager.discover([device])
    manager.designate("arduino-1")
    vigil = FakeVigil()
    router = CorelessInputRouter(manager, vigil=vigil)
    io = MemoryHostIO()
    arduino_transport = MemoryInputTransport()
    arduino_adapter = ArduinoInputAdapter(
        ArduinoSerialIO(serial, "arduino-1"), arduino_transport
    )

    system = CorelessSystem(memory_size=4096, storage_path=tmp_path / "arduino-input.img")
    system.boot()
    endpoint = HostEndpoint(
        endpoint_id="coreless-arduino-io",
        identity=CorelessIdentity("coreless-arduino-io"),
        capabilities=HostCapabilities(display=True, input=True, network=True, startup=True),
    )
    interface = CorelessHostInterface(endpoint.identity)
    adapter = MemoryHostTransportAdapter([endpoint])
    negotiated = adapter.connect(
        endpoint,
        interface,
        system=system,
        host_io=io,
        input_router=router,
    )
    assert "input" in negotiated

    # The Arduino serial adapter emits ABI frames; the ordinary host transport
    # and Coreless router consume the exact same frames as other input devices.
    assert arduino_adapter.pump_once() is True
    io.input.send_event(arduino_transport.receive_event())
    counts = interface.pump_host_io()
    assert counts["input"] == 1
    assert len(router.raw_events) == 1
    assert router.raw_events[0].event_type is InputEventType.POINTER_MOVE
    assert (router.raw_events[0].x, router.raw_events[0].y) == (12.5, 7.0)
    assert len(vigil.seen) == 1
    assert router.interpreted_events[0].source_sequence == (router.raw_events[0].sequence,)
    assert router.raw_events[0].metadata["arduino_sequence"] == 20

    # VIGIL is optional: disabling interpretation leaves raw event delivery live.
    router.enable_vigil(False)
    assert arduino_adapter.pump_once() is True
    io.input.send_event(arduino_transport.receive_event())
    counts = interface.pump_host_io()
    assert counts["input"] == 1
    assert len(router.raw_events) == 2
    assert router.raw_events[1].sequence > router.raw_events[0].sequence
    assert router.raw_events[1].metadata["arduino_sequence"] == 21
    assert len(vigil.seen) == 1
    assert len(router.interpreted_events) == 1
