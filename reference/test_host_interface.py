import sys
sys.path.insert(0, ".")

import pytest

from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities


def test_host_interface_discovers_and_verifies_coreless_identity():
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))

    identity = interface.discover()

    assert identity.computer_id == "coreless-0"
    assert identity.architecture == "Coreless-64"
    assert interface.verify(identity)
    assert not interface.verify(CorelessIdentity("other"))


def test_host_interface_negotiates_only_shared_capabilities():
    interface = CorelessHostInterface(
        CorelessIdentity("coreless-0"),
        supported={"display", "input", "network"},
    )
    host = HostCapabilities(
        display=True,
        input=True,
        network=True,
        startup=True,
        telemetry=True,
    )

    assert interface.negotiate(host) == frozenset({"display", "input", "network"})


def test_host_interface_attaches_and_binds_external_channels():
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    host = HostCapabilities(display=True, input=True, network=True, startup=True)

    negotiated = interface.attach(interface.discover(), host)
    interface.bind_channel("display", object())
    interface.bind_channel("input", object())

    assert interface.attached
    assert {"display", "input"}.issubset(negotiated)
    assert interface.channel("display") is not None


def test_host_interface_rejects_unnegotiated_channel():
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    interface.attach(interface.discover(), HostCapabilities(display=True))

    with pytest.raises(PermissionError, match="not negotiated"):
        interface.bind_channel("network", object())


def test_host_interface_detach_preserves_identity_but_closes_channels():
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    interface.attach(
        interface.discover(),
        HostCapabilities(display=True, input=True, startup=True),
    )
    interface.bind_channel("display", object())

    interface.detach()

    assert not interface.attached
    assert interface.identity.computer_id == "coreless-0"
    assert interface.channels == {}
    assert interface.negotiated == frozenset()


def test_host_interface_rejects_incompatible_protocol():
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))

    with pytest.raises(ValueError, match="protocol"):
        interface.negotiate(HostCapabilities(protocol_version=2))


def test_host_interface_requires_coreless_identity_match():
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))

    with pytest.raises(ValueError, match="identity"):
        interface.attach(
            CorelessIdentity("wrong-computer"),
            HostCapabilities(display=True),
        )
