import sys
import json
sys.path.insert(0, ".")

import pytest

from components import ComponentDescriptor, CorelessComponent, CorelessHub, Workload


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


def test_component_owns_bound_vm_lifecycle():
    from virtualization import Hypervisor

    hypervisor = Hypervisor(2)
    vm = hypervisor.create_vm(1 << 20, 1)
    component = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"}), vm_id=str(vm.vmid)),
        vm=vm,
    )

    assert component.vm_status()["running"] is False
    component.start_vm()
    assert component.vm_status()["running"] is True
    component.stop_vm()
    assert component.vm_status()["running"] is False

    vm.vcpus[0].registers[1] = 99
    vm.vcpus[0].pc = 0x100
    component.reset_vm()
    assert vm.vcpus[0].registers[1] == 0
    assert vm.vcpus[0].pc == 0
    assert component.vm_status()["running"] is False

def test_component_owns_ai_runtime_lifecycle_and_vm_boundary():
    class FakeAI:
        def __init__(self):
            self.running = False
        def start(self):
            self.running = True
        def stop(self):
            self.running = False

    component = CorelessComponent(
        ComponentDescriptor(
            "cpu-0",
            "cpu-intelligence",
            frozenset({"inference"}),
            ai_model_id="qwen3-0.6b",
            vm_id="cpu-ai-vm",
        ),
        ai_runtime=FakeAI(),
        vm=object(),
    )

    assert component.ai_status()["running"] is False
    component.start_ai()
    assert component.ai_status()["running"] is True
    assert component.ai_status()["model_id"] == "qwen3-0.6b"
    assert component.ai_status()["role"] == "cpu-intelligence"
    component.require_ai_vm()
    component.stop_ai()
    assert component.ai_status()["running"] is False

def test_hub_negotiates_capabilities_and_opens_ipc():
    from virtualization import Hypervisor

    hypervisor = Hypervisor(2)
    source_vm = hypervisor.create_vm(1 << 20, 1)
    target_vm = hypervisor.create_vm(1 << 20, 1)
    hub = CorelessHub(hypervisor=hypervisor)

    source = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute", "ipc"})),
        vm=source_vm,
    )
    target = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"graphics", "ipc"})),
        vm=target_vm,
    )
    hub.connect(source)
    hub.connect(target)

    assert hub.negotiate("cpu-0", "vision-0", {"ipc"}) == frozenset({"ipc"})
    capability = hub.open_ipc("cpu-0", "vision-0", {"ipc"})
    hub.send_ipc("cpu-0", "vision-0", b"frame")
    assert hypervisor.recv_message(target_vm.vmid, 0) == b"frame"
    hub.close_ipc("cpu-0", "vision-0")
    with pytest.raises(PermissionError, match="not been negotiated"):
        hub.send_ipc("cpu-0", "vision-0", b"again")


def test_hub_fault_isolates_component_and_revokes_ipc():
    from virtualization import Hypervisor

    hypervisor = Hypervisor(2)
    source_vm = hypervisor.create_vm(1 << 20, 1)
    target_vm = hypervisor.create_vm(1 << 20, 1)
    hub = CorelessHub(hypervisor=hypervisor)
    source = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"ipc"})),
        vm=source_vm,
    )
    target = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"ipc"})),
        vm=target_vm,
    )
    hub.connect(source)
    hub.connect(target)
    hub.open_ipc("cpu-0", "vision-0", {"ipc"})

    isolated = hub.isolate("vision-0", "vm fault")
    assert isolated is target
    assert target.healthy is False
    assert target.fault == "vm fault"
    assert target.standalone
    assert "vision-0" not in {c.component_id for c in hub.components()}
    with pytest.raises(PermissionError, match="not been negotiated"):
        hub.send_ipc("cpu-0", "vision-0", b"blocked")


def test_faulted_component_can_recover_and_rejoin():
    hub = CorelessHub()
    component = CorelessComponent(
        ComponentDescriptor("storage-0", "storage", frozenset({"storage"}))
    )
    hub.connect(component)
    hub.isolate("storage-0", "storage fault")
    assert component.healthy is False

    hub.rejoin(component)
    assert component.healthy is True
    assert component.fault is None
    assert component.hub_id == hub.hub_id
    assert hub.component("storage-0") is component


def test_faulted_component_cannot_hot_plug_until_recovered():
    hub = CorelessHub()
    component = CorelessComponent(
        ComponentDescriptor("network-0", "networking", frozenset({"network"}))
    )
    component.isolate("link failure")
    with pytest.raises(RuntimeError, match="fault-isolated"):
        hub.connect(component)


def test_hub_distributes_workload_to_specialized_component():
    from components import Workload

    cpu = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        workload_executor=lambda payload: payload * 2,
    )
    vision = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"image_processing"})),
        workload_executor=lambda payload: payload.upper(),
    )
    hub = CorelessHub()
    hub.connect(cpu)
    hub.connect(vision)

    result = hub.dispatch(Workload("w1", "image_processing", "frame"))
    assert result.component_id == "vision-0"
    assert result.result == "FRAME"


def test_hub_pipeline_distributes_each_stage_by_capability():
    from components import Workload

    cpu = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        workload_executor=lambda payload: payload + 1,
    )
    vision = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"vision"})),
        workload_executor=lambda payload: payload * 10,
    )
    hub = CorelessHub()
    hub.connect(cpu)
    hub.connect(vision)

    results = hub.dispatch_pipeline([
        Workload("compute", "compute", 4),
        Workload("vision", "vision", 3),
    ])
    assert [(r.component_id, r.result) for r in results] == [
        ("cpu-0", 5),
        ("vision-0", 30),
    ]


def test_hub_dispatch_parallel_runs_independent_component_workloads():
    from components import Workload

    cpu = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        workload_executor=lambda payload: payload + 1,
    )
    vision = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"vision"})),
        workload_executor=lambda payload: payload * 10,
    )
    hub = CorelessHub()
    hub.connect(cpu)
    hub.connect(vision)

    results = hub.dispatch_parallel([
        Workload("compute", "compute", 4),
        Workload("vision", "vision", 3),
    ])

    assert [(result.component_id, result.result) for result in results] == [
        ("cpu-0", 5),
        ("vision-0", 30),
    ]


def test_hub_dispatch_parallel_preserves_empty_input():
    assert CorelessHub().dispatch_parallel([]) == ()


def test_faulted_component_is_excluded_from_workload_dispatch():
    from components import Workload

    vision = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"vision"})),
        workload_executor=lambda payload: payload,
    )
    hub = CorelessHub()
    hub.connect(vision)
    hub.isolate("vision-0", "executor fault")

    with pytest.raises(LookupError, match="no healthy component"):
        hub.dispatch(Workload("w1", "vision", "frame"))


def test_hub_coordinates_boot_and_shutdown_without_breaking_standalone_components():
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

    system_component = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=FakeSystem(),
    )
    standalone = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"vision"})),
    )
    hub = CorelessHub()
    hub.connect(system_component)
    hub.connect(standalone)

    assert hub.boot("/coreless-init") == ("cpu-0",)
    assert system_component.system.machine.booted is True
    assert standalone.standalone is False
    assert hub.lifecycle_status()["booted_components"] == ("cpu-0",)

    assert hub.shutdown() == ("cpu-0",)
    assert system_component.system.machine.booted is False
    assert hub.components() == (system_component, standalone)


def test_hub_coordinates_checkpoint_and_restore_across_component_machines():
    class FakeStorage:
        def __init__(self):
            self.objects = {}
        def put(self, key, value, sync=False):
            self.objects[key] = bytes(value)
        def sync(self):
            pass

    class FakeMachine:
        def __init__(self):
            self.storage = FakeStorage()

    class FakeSystem:
        def __init__(self):
            self.machine = FakeMachine()
            self.checkpoints = []
            self.restored = []
        def checkpoint(self, name):
            self.checkpoints.append(name)
            return f"hash:{name}"
        def restore(self, name):
            self.restored.append(name)
            return self

    first_system = FakeSystem()
    second_system = FakeSystem()
    first = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=first_system,
    )
    second = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"vision"})),
        system=second_system,
    )
    standalone = CorelessComponent(
        ComponentDescriptor("network-0", "network", frozenset({"network"})),
    )
    hub = CorelessHub("hub-checkpoint")
    hub.connect(first)
    hub.connect(second)
    hub.connect(standalone)

    result = hub.checkpoint("snapshot")
    assert result == {
        "hub_id": "hub-checkpoint",
        "checkpoints": {
            "cpu-0": "hash:snapshot-cpu-0",
            "vision-0": "hash:snapshot-vision-0",
        },
        "committed": True,
        "manifest_version": hub.VERSION,
        "component_count": 2,
    }
    assert first_system.checkpoints == ["snapshot-cpu-0"]
    assert second_system.checkpoints == ["snapshot-vision-0"]
    assert first.restore_identity() == first.descriptor
    assert second.restore_identity() == second.descriptor

    assert hub.restore("snapshot") == ("cpu-0", "vision-0")
    assert first_system.restored == ["snapshot-cpu-0"]
    assert second_system.restored == ["snapshot-vision-0"]
    assert standalone.standalone is False


def test_hub_checkpoint_does_not_publish_manifest_when_component_checkpoint_fails():
    class FakeStorage:
        def __init__(self):
            self.objects = {}
            self.sync_count = 0

        def put(self, key, value, sync=False):
            self.objects[key] = bytes(value)

        def sync(self):
            self.sync_count += 1

    class FakeMachine:
        def __init__(self):
            self.storage = FakeStorage()

    class FakeSystem:
        def __init__(self, *, fail=False):
            self.machine = FakeMachine()
            self.fail = fail
            self.checkpoints = []

        def checkpoint(self, name):
            if self.fail:
                raise RuntimeError("checkpoint failed")
            self.checkpoints.append(name)
            return f"hash:{name}"

    first_system = FakeSystem()
    second_system = FakeSystem(fail=True)
    first = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=first_system,
    )
    second = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"vision"})),
        system=second_system,
    )
    hub = CorelessHub("hub-atomic")
    hub.connect(first)
    hub.connect(second)

    with pytest.raises(RuntimeError, match="checkpoint failed"):
        hub.checkpoint("snapshot")

    checkpoint_key = "machine/hub/hub-atomic/checkpoint"
    assert checkpoint_key not in first_system.machine.storage.objects
    assert checkpoint_key not in second_system.machine.storage.objects
    assert first_system.checkpoints == ["snapshot-cpu-0"]
    assert first_system.machine.storage.sync_count == 0
    assert second_system.machine.storage.sync_count == 0


def test_hub_checkpoint_rejects_missing_component_storage_before_snapshot():
    class FakeSystem:
        def __init__(self, storage):
            self.machine = type("Machine", (), {"storage": storage})()
            self.checkpoints = []

        def checkpoint(self, name):
            self.checkpoints.append(name)
            return name

    class Storage:
        def __init__(self):
            self.objects = {}

        def put(self, key, value, sync=False):
            self.objects[key] = bytes(value)

    first = FakeSystem(Storage())
    second = FakeSystem(None)
    hub = CorelessHub("hub-preflight-storage")
    hub.connect(CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=first,
    ))
    hub.connect(CorelessComponent(
        ComponentDescriptor("mem-0", "memory", frozenset({"memory"})),
        system=second,
    ))

    try:
        hub.checkpoint("snapshot")
        assert False, "checkpoint should reject missing persistent storage"
    except RuntimeError as exc:
        assert "mem-0" in str(exc)

    assert first.checkpoints == []
    assert first.machine.storage.objects == {}



def test_hub_restore_rejects_corrupt_manifest_before_mutation():
    class Storage:
        def __init__(self):
            self.objects = {}

    class FakeSystem:
        def __init__(self):
            self.machine = type("Machine", (), {"storage": Storage()})()
            self.restored = []

        def restore(self, name):
            self.restored.append(name)

        def checkpoint(self, name):
            return name

    first = FakeSystem()
    second = FakeSystem()
    hub = CorelessHub("hub-corrupt-manifest")
    hub.connect(CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=first,
    ))
    hub.connect(CorelessComponent(
        ComponentDescriptor("mem-0", "memory", frozenset({"memory"})),
        system=second,
    ))
    key = "machine/hub/hub-corrupt-manifest/checkpoint"
    first.machine.storage.objects[key] = b"not-json"
    second.machine.storage.objects[key] = b"not-json"

    try:
        hub.restore("snapshot")
        assert False, "restore should reject corrupt manifest"
    except ValueError as exc:
        assert "invalid Coreless Hub checkpoint manifest" in str(exc)

    assert first.restored == []
    assert second.restored == []



def test_hub_restore_rejects_malformed_manifest_schema_before_mutation():
    class Storage:
        def __init__(self):
            self.objects = {}

    class FakeSystem:
        def __init__(self):
            self.machine = type("Machine", (), {"storage": Storage()})()
            self.restored = []

        def restore(self, name):
            self.restored.append(name)

        def checkpoint(self, name):
            return name

    first = FakeSystem()
    second = FakeSystem()
    hub = CorelessHub("hub-schema-manifest")
    hub.connect(CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=first,
    ))
    hub.connect(CorelessComponent(
        ComponentDescriptor("mem-0", "memory", frozenset({"memory"})),
        system=second,
    ))
    key = "machine/hub/hub-schema-manifest/checkpoint"
    malformed = json.dumps({
        "version": 1,
        "hub_id": "hub-schema-manifest",
        "components": ["cpu-0", "mem-0"],
        "checkpoints": ["not", "a", "mapping"],
    }).encode("utf-8")
    first.machine.storage.objects[key] = malformed
    second.machine.storage.objects[key] = malformed

    try:
        hub.restore("snapshot")
        assert False, "restore should reject malformed checkpoint map"
    except ValueError as exc:
        assert "invalid Coreless Hub checkpoint map" in str(exc)

    assert first.restored == []
    assert second.restored == []



def test_hub_restore_rejects_incomplete_checkpoint_coverage():
    class Storage:
        def __init__(self):
            self.objects = {}

    class FakeSystem:
        def __init__(self):
            self.machine = type("Machine", (), {"storage": Storage()})()
            self.restored = []

        def restore(self, name):
            self.restored.append(name)

        def checkpoint(self, name):
            return name

    first = FakeSystem()
    second = FakeSystem()
    hub = CorelessHub("hub-coverage-manifest")
    hub.connect(CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=first,
    ))
    hub.connect(CorelessComponent(
        ComponentDescriptor("mem-0", "memory", frozenset({"memory"})),
        system=second,
    ))
    key = "machine/hub/hub-coverage-manifest/checkpoint"
    manifest = json.dumps({
        "version": 1,
        "hub_id": "hub-coverage-manifest",
        "components": ["cpu-0", "mem-0"],
        "checkpoints": {"cpu-0": "snapshot-cpu-0"},
    }).encode("utf-8")
    first.machine.storage.objects[key] = manifest
    second.machine.storage.objects[key] = manifest

    try:
        hub.restore("snapshot")
        assert False, "restore should reject incomplete checkpoint coverage"
    except ValueError as exc:
        assert "checkpoint coverage mismatch" in str(exc)

    assert first.restored == []
    assert second.restored == []



def test_hub_restore_rejects_missing_manifest_on_any_persistent_component():
    class FakeStorage:
        def __init__(self):
            self.objects = {}

    class FakeMachine:
        def __init__(self):
            self.storage = FakeStorage()

    class FakeSystem:
        def __init__(self):
            self.machine = FakeMachine()
            self.restored = []
        def restore(self, name):
            self.restored.append(name)
            return self

    first_system = FakeSystem()
    second_system = FakeSystem()
    first = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=first_system,
    )
    second = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"vision"})),
        system=second_system,
    )
    hub = CorelessHub("hub-committed")
    hub.connect(first)
    hub.connect(second)

    manifest = {
        "version": hub.VERSION,
        "hub_id": hub.hub_id,
        "components": ["cpu-0", "vision-0"],
        "checkpoints": {
            "cpu-0": "snapshot-cpu-0",
            "vision-0": "snapshot-vision-0",
        },
    }
    key = "machine/hub/hub-committed/checkpoint"
    first_system.machine.storage.objects[key] = json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    with pytest.raises(KeyError, match="committed Coreless Hub checkpoint"):
        hub.restore("snapshot")

    assert first_system.restored == []
    assert second_system.restored == []


def test_hub_restore_rolls_back_already_restored_components_on_failure():
    class FakeStorage:
        def __init__(self):
            self.objects = {}

    class FakeMachine:
        def __init__(self):
            self.storage = FakeStorage()

    class FakeSystem:
        def __init__(self, *, fail_restore=False):
            self.machine = FakeMachine()
            self.restored = []
            self.checkpoints = []
            self.fail_restore = fail_restore

        def checkpoint(self, name):
            self.checkpoints.append(name)
            return f"hash:{name}"

        def restore(self, name):
            if self.fail_restore and name == "snapshot-vision-0":
                raise RuntimeError("restore failed")
            self.restored.append(name)
            return self

    first_system = FakeSystem()
    second_system = FakeSystem(fail_restore=True)
    first = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=first_system,
    )
    second = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"vision"})),
        system=second_system,
    )
    first.restore_identity = lambda: first.descriptor
    second.restore_identity = lambda: second.descriptor

    hub = CorelessHub("hub-rollback")
    hub.connect(first)
    hub.connect(second)

    manifest = {
        "version": hub.VERSION,
        "hub_id": hub.hub_id,
        "components": ["cpu-0", "vision-0"],
        "checkpoints": {
            "cpu-0": "snapshot-cpu-0",
            "vision-0": "snapshot-vision-0",
        },
    }
    key = "machine/hub/hub-rollback/checkpoint"
    encoded = json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    first_system.machine.storage.objects[key] = encoded
    second_system.machine.storage.objects[key] = encoded

    with pytest.raises(RuntimeError, match="restore failed"):
        hub.restore("snapshot")

    assert first_system.restored == [
        "snapshot-cpu-0",
        "snapshot-rollback-hub-rollback-cpu-0",
    ]
    assert second_system.restored == [
        "snapshot-rollback-hub-rollback-vision-0",
    ]


def test_hub_restore_preflights_all_manifests_before_restoring_any_component():
    class FakeStorage:
        def __init__(self):
            self.objects = {}

    class FakeMachine:
        def __init__(self):
            self.storage = FakeStorage()

    class FakeSystem:
        def __init__(self):
            self.machine = FakeMachine()
            self.restored = []

        def restore(self, name):
            self.restored.append(name)
            return self

    first_system = FakeSystem()
    second_system = FakeSystem()
    first = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=first_system,
    )
    second = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"vision"})),
        system=second_system,
    )
    hub = CorelessHub("hub-preflight")
    hub.connect(first)
    hub.connect(second)

    manifest = {
        "version": hub.VERSION,
        "hub_id": hub.hub_id,
        "components": ["cpu-0", "vision-0"],
        "checkpoints": {
            "cpu-0": "snapshot-cpu-0",
            "vision-0": "snapshot-vision-0",
        },
    }
    key = "machine/hub/hub-preflight/checkpoint"
    encoded = json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    first_system.machine.storage.objects[key] = encoded

    invalid = dict(manifest)
    invalid["hub_id"] = "wrong-hub"
    second_system.machine.storage.objects[key] = json.dumps(
        invalid, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    with pytest.raises(ValueError, match="manifest mismatch"):
        hub.restore("snapshot")

    assert first_system.restored == []
    assert second_system.restored == []


def test_hub_checkpoint_rejects_manifest_change_after_durability_sync():
    class MutatingStorage:
        def __init__(self):
            self.objects = {}
            self.sync_count = 0

        def put(self, key, value, sync=False):
            self.objects[key] = bytes(value)

        def sync(self):
            self.sync_count += 1
            if self.sync_count == 2:
                self.objects["machine/hub/hub-durable/checkpoint"] = b"mutated"

        def list_checkpoints(self):
            return tuple(
                key.split("/", 1)[1]
                for key in self.objects
                if key.startswith("checkpoint/")
            )

    class FakeMachine:
        def __init__(self):
            self.storage = MutatingStorage()

    class FakeSystem:
        def __init__(self):
            self.machine = FakeMachine()

        def checkpoint(self, name):
            self.machine.storage.objects[f"checkpoint/{name}"] = b"checkpoint"

    first = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=FakeSystem(),
    )
    second = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"vision"})),
        system=FakeSystem(),
    )
    hub = CorelessHub("hub-durable")
    hub.connect(first)
    hub.connect(second)

    with pytest.raises(RuntimeError, match="manifest changed after durability sync"):
        hub.checkpoint("snapshot")


def test_hub_checkpoint_failed_commit_restores_previous_manifest():
    class FakeStorage:
        def __init__(self, corrupt=False):
            self.objects = {"machine/hub/hub-rollback/checkpoint": b"old-manifest"}
            self.corrupt = corrupt

        def put(self, key, value, sync=False):
            self.objects[key] = b"corrupt" if self.corrupt else bytes(value)

        def sync(self):
            pass

    class FakeMachine:
        def __init__(self, storage):
            self.storage = storage

    class FakeSystem:
        def __init__(self, storage):
            self.machine = FakeMachine(storage)

        def checkpoint(self, name):
            return name

    first = FakeSystem(FakeStorage())
    second = FakeSystem(FakeStorage(corrupt=True))
    hub = CorelessHub("hub-rollback")
    hub.connect(CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})), system=first))
    hub.connect(CorelessComponent(
        ComponentDescriptor("mem-0", "memory", frozenset({"memory"})), system=second))

    with pytest.raises(RuntimeError, match="commit verification failed"):
        hub.checkpoint("snapshot")

    key = "machine/hub/hub-rollback/checkpoint"
    assert first.machine.storage.objects[key] == b"old-manifest"
    assert second.machine.storage.objects[key] == b"old-manifest"


def test_hub_checkpoint_rejects_failed_commit_verification():
    class FakeStorage:
        def __init__(self, corrupt=False):
            self.objects = {}
            self.corrupt = corrupt

        def put(self, key, value, sync=False):
            self.objects[key] = b"corrupt" if self.corrupt else bytes(value)

        def sync(self):
            pass

    class FakeMachine:
        def __init__(self, storage):
            self.storage = storage

    class FakeSystem:
        def __init__(self, storage):
            self.machine = FakeMachine(storage)
            self.checkpoints = []

        def checkpoint(self, name):
            self.checkpoints.append(name)
            return f"hash:{name}"

    first = FakeSystem(FakeStorage())
    second = FakeSystem(FakeStorage(corrupt=True))
    hub = CorelessHub("hub-commit-verify")
    hub.connect(CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"})),
        system=first,
    ))
    hub.connect(CorelessComponent(
        ComponentDescriptor("mem-0", "memory", frozenset({"memory"})),
        system=second,
    ))

    with pytest.raises(RuntimeError, match="commit verification failed"):
        hub.checkpoint("snapshot")

    key = "machine/hub/hub-commit-verify/checkpoint"
    assert key not in first.machine.storage.objects
    assert key not in second.machine.storage.objects


def test_component_executes_bound_vm_through_native_cpu():
    from core import CorelessCPU
    from virtualization import Hypervisor
    h = Hypervisor(1)
    vm = h.create_vm(1 << 16, 1)
    cpu = CorelessCPU(memory_size=1 << 16)
    h.bind_cpu(vm.vmid, cpu)
    cpu.memory[0:4] = ((1 << 27) | (1 << 22) | 23).to_bytes(4, "little")
    component = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"}), vm_id=str(vm.vmid)),
        vm=vm,
    )
    h.run(vm.vmid)
    assert component.execute_vm_steps(h) == 1
    assert vm.vcpus[0].registers[1] == 23


def test_component_can_execute_vm_through_its_unified_hub():
    from core import CorelessCPU
    from virtualization import Hypervisor

    hypervisor = Hypervisor(1)
    vm = hypervisor.create_vm(1 << 16, 1)
    cpu = CorelessCPU(memory_size=1 << 16)
    hypervisor.bind_cpu(vm.vmid, cpu)
    cpu.memory[0:4] = ((1 << 27) | (1 << 22) | 31).to_bytes(4, "little")
    component = CorelessComponent(
        ComponentDescriptor("cpu-0", "cpu", frozenset({"compute"}), vm_id=str(vm.vmid)),
        vm=vm,
    )
    hub = CorelessHub("hub-exec", hypervisor=hypervisor)
    hub.connect(component)
    hypervisor.run(vm.vmid)

    assert component.execute_hub_vm_steps(hub) == 1
    assert vm.vcpus[0].registers[1] == 31


def test_component_can_execute_through_its_unified_hub():
    component = CorelessComponent(
        ComponentDescriptor("vision-0", "vision", frozenset({"image_processing"})),
        workload_executor=lambda payload: payload.upper(),
    )
    hub = CorelessHub()
    hub.connect(component)
    result = component.execute_hub_workload(hub, Workload("w1", "image_processing", "frame"))
    assert result.component_id == "vision-0"
    assert result.result == "FRAME"

