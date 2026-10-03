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


def test_host_interface_can_boot_and_resume_bound_coreless_system():
    from system import CorelessSystem

    system = CorelessSystem()
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    interface.attach(
        interface.discover(),
        HostCapabilities(startup=True),
        system=system,
    )

    assert interface.boot("/init") is system
    assert system.machine.booted
    assert interface.resume() is system


def test_host_interface_detach_does_not_shutdown_bound_system():
    from system import CorelessSystem

    system = CorelessSystem()
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    interface.attach(
        interface.discover(),
        HostCapabilities(startup=True),
        system=system,
    )
    interface.boot()

    interface.detach()

    assert not interface.attached
    assert system.machine.booted
    assert interface.system is system


def test_host_interface_requires_startup_capability_to_boot():
    from system import CorelessSystem

    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    interface.attach(interface.discover(), HostCapabilities(display=True), system=CorelessSystem())

    with pytest.raises(PermissionError, match="startup"):
        interface.boot()


def test_host_interface_binds_coreless_hub_and_exposes_unified_composition():
    from components import ComponentDescriptor, CorelessComponent, CorelessHub

    hub = CorelessHub("hub-0")
    cpu = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute", "inference"}))
    )
    vision = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"graphics"}))
    )
    hub.connect(cpu)
    hub.connect(vision)

    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    interface.attach(
        interface.discover(),
        HostCapabilities(startup=True, display=True),
    )
    interface.attach_hub(hub)

    assert {c.component_id for c in interface.hub_components()} == {"cpu-0", "vision-0"}
    assert interface.hub_capabilities() == frozenset({"compute", "inference", "graphics"})
    assert interface.status()["hub_component_count"] == 2


def test_host_detach_releases_external_attachment_but_preserves_hub():
    from components import CorelessHub

    hub = CorelessHub("hub-0")
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    interface.attach(interface.discover(), HostCapabilities(display=True))
    interface.attach_hub(hub)

    interface.detach()

    assert interface.hub is hub
    assert interface.status()["hub_bound"] is True


def test_host_interface_coordinates_hub_boot_resume_and_shutdown():
    from components import ComponentDescriptor, CorelessComponent, CorelessHub

    class FakeSystem:
        def __init__(self):
            self.machine = type("Machine", (), {"booted": False})()
            self.boot_manifest = None
        def boot(self, init_path="/init"):
            self.machine.booted = True
            self.boot_manifest = {"init": init_path}
        def shutdown(self):
            self.machine.booted = False
            return self

    system = FakeSystem()
    component = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=system,
    )
    hub = CorelessHub("hub-0")
    hub.connect(component)

    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    interface.attach(
        interface.discover(),
        HostCapabilities(startup=True),
    )
    interface.attach_hub(hub)

    assert interface.boot_hub("/hub-init") == ("cpu-0",)
    assert system.machine.booted
    assert interface.resume() == ("cpu-0",)
    assert interface.shutdown_hub() == ("cpu-0",)
    assert not system.machine.booted


def test_host_interface_coordinates_hub_checkpoint_and_restore():
    from components import ComponentDescriptor, CorelessComponent, CorelessHub

    class FakeStorage:
        def __init__(self):
            self.objects = {}
        def put(self, key, value, sync=False):
            self.objects[key] = bytes(value)
        def sync(self):
            pass

    class FakeSystem:
        def __init__(self):
            self.machine = type("Machine", (), {"storage": FakeStorage()})()
            self.checkpoints = []
            self.restored = []
        def checkpoint(self, name):
            self.checkpoints.append(name)
            return name
        def restore(self, name):
            self.restored.append(name)
            return self

    system = FakeSystem()
    component = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=system,
    )
    hub = CorelessHub("hub-0")
    hub.connect(component)

    interface = CorelessHostInterface(CorelessIdentity("coreless-0"), {"display", "input", "network", "startup", "management"})
    interface.attach(
        interface.discover(),
        HostCapabilities(startup=True, management=True),
    )
    interface.attach_hub(hub)

    assert interface.checkpoint_hub("snapshot")["hub_id"] == "hub-0"
    assert system.checkpoints == ["snapshot-cpu-0"]
    assert interface.restore_hub("snapshot") == ("cpu-0",)
    assert system.restored == ["snapshot-cpu-0"]
