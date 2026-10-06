import sys
sys.path.insert(0, ".")

from device_protocol import (
    ARCHITECTURE_CORELESS64,
    DEVICE_TYPE_CORELESS64,
    DeviceIdentityFrame,
    capability_bits,
)
from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities


def test_identity_attach_negotiate_is_limited_by_device_advertisement():
    interface = CorelessHostInterface(
        CorelessIdentity("coreless-filter"),
        supported={"display", "input", "network", "startup"},
    )
    frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits({"display", "startup"}),
        payload=b"coreless-filter",
    ).encode()

    negotiated = interface.attach_identity_frame(
        frame,
        HostCapabilities(display=True, input=True, network=True, startup=True),
    )

    assert negotiated == frozenset({"display", "startup"})
    assert interface.negotiated == frozenset({"display", "startup"})
