import sys
sys.path.insert(0, ".")

import pytest

from components import ComponentDescriptor, CorelessComponent, CorelessHub


def test_component_is_complete_and_standalone():
    component = CorelessComponent(
        ComponentDescriptor(
            component_id="cpu-0",
            role="cpu-intelligence",
            capabilities=frozenset({"scalar_compute", "inference"}),
            ai_model_id="qwen3-0.6b",
            vm_id="cpu-ai-vm",
        ),
        ai_runtime=object(),
        vm=object(),
    )

    status = component.status()

    assert component.standalone
    assert status["ai_integrated"] is True
    assert status["vm_integrated"] is True
    assert status["component"]["role"] == "cpu-intelligence"


def test_hub_discovers_and_composes_specialized_components():
    hub = CorelessHub()
    cpu = CorelessComponent(
        ComponentDescriptor(
            component_id="cpu-0",
            role="cpu-intelligence",
            capabilities=frozenset({"scalar_compute", "inference"}),
            ai_model_id="qwen3-0.6b",
            vm_id="cpu-ai-vm",
        )
    )
    vision = CorelessComponent(
        ComponentDescriptor(
            component_id="vision-0",
            role="vision",
            capabilities=frozenset({"graphics", "image_processing"}),
            ai_model_id="vision-specialist",
            vm_id="vision-ai-vm",
        )
    )

    hub.connect(cpu)
    hub.connect(vision)

    assert not cpu.standalone
    assert not vision.standalone
    assert {item.component_id for item in hub.discover()} == {
        "cpu-0",
        "vision-0",
    }
    assert hub.capabilities() == frozenset(
        {"scalar_compute", "inference", "graphics", "image_processing"}
    )
    assert hub.composition()["component_count"] == 2
    assert hub.composition()["unified"] is True


def test_component_can_disconnect_and_continue_independently():
    hub = CorelessHub()
    component = CorelessComponent(
        ComponentDescriptor(
            component_id="storage-0",
            role="storage",
            capabilities=frozenset({"persistent_storage"}),
            ai_model_id="storage-specialist",
            vm_id="storage-ai-vm",
        )
    )

    hub.connect(component)
    detached = hub.disconnect("storage-0")

    assert detached is component
    assert component.standalone
    assert component.hub_id is None
    assert hub.components() == ()


def test_component_cannot_be_claimed_by_two_hubs():
    first = CorelessHub("hub-a")
    second = CorelessHub("hub-b")
    component = CorelessComponent(
        ComponentDescriptor(
            component_id="network-0",
            role="networking",
            capabilities=frozenset({"packet_processing"}),
        )
    )

    first.connect(component)
    with pytest.raises(ValueError, match="already attached"):
        second.connect(component)


def test_component_delegates_lifecycle_to_coreless_system():
    class FakeStorage:
        def put(self, key, value, sync=False):
            pass

    class FakeMachine:
        def __init__(self):
            self.storage = FakeStorage()

    class FakeSystem:
        def __init__(self):
            self.machine = FakeMachine()
            self.booted = False
        def boot(self):
            self.booted = True
        def shutdown(self):
            self.booted = False
            return self

    system = FakeSystem()
    component = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=system,
    )
    component.boot()
    assert system.booted
    assert component.status()["system_integrated"] is True
    component.shutdown()
    assert not system.booted


def test_component_persists_and_restores_identity():
    class FakeStorage:
        def __init__(self):
            self.objects = {}
        def put(self, key, value, sync=False):
            self.objects[key] = value

    class FakeMachine:
        def __init__(self):
            self.storage = FakeStorage()

    class FakeSystem:
        def __init__(self):
            self.machine = FakeMachine()
            self.booted = False
        def boot(self):
            self.booted = True

    descriptor = ComponentDescriptor(
        "vision-0",
        "vision",
        frozenset({"graphics", "image_processing"}),
        ai_model_id="vision-specialist",
        vm_id="vision-ai-vm",
    )
    system = FakeSystem()
    component = CorelessComponent(descriptor, system=system)

    component.boot()
    restored = component.restore_identity()

    assert system.booted
    assert restored == descriptor
    assert system.machine.storage.objects[component.persistence_key]
