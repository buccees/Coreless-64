import pytest

from storage import PersistentMachineImage, StorageRegionPolicy


def make_policy():
    policy = StorageRegionPolicy()
    policy.register_region("ram", ("ram/",), mutable=True)
    policy.register_region("state", ("state/",), mutable=True)
    policy.register_region("models", ("models/",), mutable=False)
    return policy


def test_policy_is_opt_in_and_existing_storage_behavior_is_unchanged(tmp_path):
    disk = tmp_path / "legacy.img"
    image = PersistentMachineImage(disk)
    image.put("legacy/object", b"works")
    assert PersistentMachineImage(disk).get("legacy/object") == b"works"


def test_put_and_ram_page_enforce_policy_before_mutating_objects():
    image = PersistentMachineImage(policy=make_policy())
    image.put("state/session", b"allowed", sync=False)
    image.put_ram_page("ram/main", 0, bytes(4096), sync=False)
    assert image.get("state/session") == b"allowed"
    assert len(image.get_ram_page("main", 0)) == 4096

    with pytest.raises(PermissionError, match="immutable"):
        image.put("models/qwen3/weights.bin", b"no", sync=False)
    with pytest.raises(ValueError, match="no registered storage region"):
        image.put("unclassified/object", b"no", sync=False)
    immutable_ram_policy = StorageRegionPolicy()
    immutable_ram_policy.register_region("ram", ("ram/",), mutable=False)
    immutable_ram = PersistentMachineImage(policy=immutable_ram_policy)
    with pytest.raises(PermissionError, match="immutable"):
        immutable_ram.put_ram_page("main", 0, bytes(4096), sync=False)

    assert "models/qwen3/weights.bin" not in image.objects
    assert "unclassified/object" not in image.objects


def test_checkpoint_restore_policy_rejection_is_atomic(tmp_path):
    image = PersistentMachineImage(tmp_path / "restore.img")
    image.put("state/session", b"before")
    image.create_checkpoint("before-change")
    image.put("state/session", b"after")

    # Enable policy after creating the legacy-compatible checkpoint so this
    # test isolates restore-time validation rather than checkpoint naming.
    policy = StorageRegionPolicy()
    policy.register_region("state", ("state/",), mutable=True)
    policy.register_region("models", ("models/",), mutable=False)
    image.objects.pop("machine", None)
    image.policy = policy
    image.put("models/weights", b"protected", sync=False)
    before_objects = dict(image.objects)
    before_metadata = dict(image.metadata)

    # The checkpoint would remove the model object; restoring must reject that
    # change before changing either the live object map or metadata.
    with pytest.raises(PermissionError, match="immutable"):
        image.restore_checkpoint("before-change")

    assert image.objects == before_objects
    assert image.metadata == before_metadata

 
def test_policy_can_classify_root_objects_used_by_machine_checkpoints():
    policy = StorageRegionPolicy()
    policy.register_region(
        "state", ("state/",), mutable=True, object_names=("machine", "filesystem")
    )
    policy.register_region("checkpoints", ("checkpoint/",), mutable=True)
    image = PersistentMachineImage(policy=policy)
    image.put("state/session", b"before", sync=False)
    image.create_checkpoint("baseline")
    image.put("state/session", b"after", sync=False)

    image.restore_checkpoint("baseline")
    assert image.get("state/session") == b"before"
    assert "machine" not in image.objects
    assert image.list_checkpoints() == ["baseline"]
