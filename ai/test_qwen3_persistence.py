import json

import pytest

from ai.qwen3 import Qwen3KVCache
from ai.tensor import Tensor
from ai.tensor_runtime import TensorRuntime
from reference.storage import PersistentMachineImage


def _tensor(seed):
    return Tensor.from_values((1, 2, 2), (seed, seed + 1, seed + 2, seed + 3))


def _cache(runtime, seed):
    cache = Qwen3KVCache.create(2, runtime)
    cache.append(0, _tensor(seed), _tensor(seed + 10))
    cache.append(1, _tensor(seed + 20), _tensor(seed + 30))
    return cache


@pytest.mark.parametrize("fail_at", [1, 2, 3, 4])
def test_failed_kv_cache_persist_keeps_previous_committed_snapshot(fail_at):
    image = PersistentMachineImage()
    runtime = TensorRuntime(image)
    old_cache = _cache(runtime, 1)
    old_cache.persist(runtime, "session")
    old_manifest = image.objects["tensor/session_manifest"]

    original_put = image.put
    calls = 0

    def fail_during_new_snapshot(name, data, sync=True):
        nonlocal calls
        if name.startswith("tensor/session_snapshot_2_"):
            calls += 1
            original_put(name, data, sync=sync)
            if calls == fail_at:
                raise OSError("injected partial tensor write")
            return
        original_put(name, data, sync=sync)

    image.put = fail_during_new_snapshot
    with pytest.raises(OSError, match="injected partial tensor write"):
        _cache(runtime, 100).persist(runtime, "session")

    assert image.objects["tensor/session_manifest"] == old_manifest
    restored = Qwen3KVCache.restore(runtime, "session", 2)
    assert restored.sequence_length == old_cache.sequence_length
    for actual, expected in zip(restored.keys, old_cache.keys):
        assert actual.data == expected.data
    for actual, expected in zip(restored.values, old_cache.values):
        assert actual.data == expected.data


def test_kv_cache_manifest_commits_complete_snapshot_and_survives_reopen(tmp_path):
    path = tmp_path / "machine.json"
    image = PersistentMachineImage(path)
    runtime = TensorRuntime(image)
    expected = _cache(runtime, 5)
    expected.persist(runtime, "session")
    image.create_checkpoint("before-reopen")

    reopened = PersistentMachineImage(path)
    restored = Qwen3KVCache.restore(TensorRuntime(reopened), "session", 2)
    assert restored.sequence_length == expected.sequence_length
    assert [item.data for item in restored.keys] == [item.data for item in expected.keys]
    assert [item.data for item in restored.values] == [item.data for item in expected.values]


def test_kv_cache_restore_supports_legacy_tensor_names():
    image = PersistentMachineImage()
    runtime = TensorRuntime(image)
    runtime.save("legacy_layer_0_key", _tensor(1))
    runtime.save("legacy_layer_0_value", _tensor(11))

    restored = Qwen3KVCache.restore(runtime, "legacy", 2)

    assert restored.sequence_length == 1
    assert restored.keys[0].data == _tensor(1).data
    assert restored.values[0].data == _tensor(11).data
    assert restored.keys[1] is None
    assert restored.values[1] is None


def test_kv_cache_restore_rejects_corrupt_manifest():
    image = PersistentMachineImage()
    image.put("tensor/session_manifest", b'{"version":1,"generation":"bad"}')
    with pytest.raises(ValueError, match="invalid Qwen3 KV cache manifest"):
        Qwen3KVCache.restore(TensorRuntime(image), "session", 2)

def test_manifest_sync_failure_rolls_back_published_pointer(monkeypatch, tmp_path):
    path = tmp_path / "machine.json"
    image = PersistentMachineImage(path)
    runtime = TensorRuntime(image)
    old_cache = _cache(runtime, 7)
    old_cache.persist(runtime, "session")
    old_manifest = image.objects["tensor/session_manifest"]

    original_sync = image.sync

    def fail_new_manifest_sync():
        raw = image.objects.get("tensor/session_manifest", b"")
        try:
            generation = json.loads(raw.decode("utf-8")).get("generation")
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            generation = None
        if generation == 2:
            raise OSError("injected manifest durability failure")
        return original_sync()

    monkeypatch.setattr(image, "sync", fail_new_manifest_sync)
    with pytest.raises(OSError, match="injected manifest durability failure"):
        _cache(runtime, 200).persist(runtime, "session")

    assert image.objects["tensor/session_manifest"] == old_manifest
    restored = Qwen3KVCache.restore(runtime, "session", 2)
    assert [item.data for item in restored.keys] == [item.data for item in old_cache.keys]
    assert [item.data for item in restored.values] == [item.data for item in old_cache.values]

    # The failed commit must not replace the durable manifest on disk either.
    reopened = PersistentMachineImage(path)
    reopened_cache = Qwen3KVCache.restore(TensorRuntime(reopened), "session", 2)
    assert [item.data for item in reopened_cache.keys] == [item.data for item in old_cache.keys]
    assert [item.data for item in reopened_cache.values] == [item.data for item in old_cache.values]

def test_restore_rejects_committed_snapshot_with_missing_tensor():
    image = PersistentMachineImage()
    runtime = TensorRuntime(image)
    _cache(runtime, 9).persist(runtime, "session")
    manifest = json.loads(image.objects["tensor/session_manifest"].decode("utf-8"))
    generation = manifest["generation"]
    image.objects.pop(f"tensor/session_snapshot_{generation}_layer_1_value")

    with pytest.raises(ValueError, match="committed Qwen3 KV cache snapshot is incomplete"):
        Qwen3KVCache.restore(runtime, "session", 2)


def test_restore_rejects_corrupt_committed_tensor_payload():
    image = PersistentMachineImage()
    runtime = TensorRuntime(image)
    _cache(runtime, 13).persist(runtime, "session")
    manifest = json.loads(image.objects["tensor/session_manifest"].decode("utf-8"))
    generation = manifest["generation"]
    image.objects[f"tensor/session_snapshot_{generation}_layer_0_key"] = b"{not-json"

    with pytest.raises(ValueError, match="invalid persisted tensor payload"):
        Qwen3KVCache.restore(runtime, "session", 2)

def test_first_manifest_sync_failure_leaves_no_committed_snapshot(monkeypatch, tmp_path):
    path = tmp_path / "first-save.json"
    image = PersistentMachineImage(path)
    runtime = TensorRuntime(image)
    original_sync = image.sync

    def fail_manifest_sync():
        if "tensor/session_manifest" in image.objects:
            raise OSError("injected first manifest durability failure")
        return original_sync()

    monkeypatch.setattr(image, "sync", fail_manifest_sync)
    with pytest.raises(OSError, match="injected first manifest durability failure"):
        _cache(runtime, 300).persist(runtime, "session")

    assert "tensor/session_manifest" not in image.objects
    # No manifest means restore must not discover orphaned generation tensors.
    restored = Qwen3KVCache.restore(runtime, "session", 2)
    assert restored.sequence_length == 0
    assert restored.keys == [None, None]
    assert restored.values == [None, None]

    reopened = PersistentMachineImage(path)
    reopened_cache = Qwen3KVCache.restore(TensorRuntime(reopened), "session", 2)
    assert reopened_cache.sequence_length == 0
    assert reopened_cache.keys == [None, None]
    assert reopened_cache.values == [None, None]


def test_manifest_sync_that_fails_after_disk_replace_rolls_back_durably(monkeypatch, tmp_path):
    path = tmp_path / "ambiguous-commit.json"
    image = PersistentMachineImage(path)
    runtime = TensorRuntime(image)
    old_cache = _cache(runtime, 17)
    old_cache.persist(runtime, "session")
    old_manifest = image.objects["tensor/session_manifest"]
    original_sync = image.sync
    failed_once = False

    def sync_then_report_failure():
        nonlocal failed_once
        if not failed_once:
            raw = image.objects.get("tensor/session_manifest", b"")
            try:
                generation = json.loads(raw.decode("utf-8")).get("generation")
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                generation = None
            if generation == 2:
                failed_once = True
                original_sync()  # Simulate replacement succeeding before error.
                raise OSError("injected post-replace durability error")
        return original_sync()

    monkeypatch.setattr(image, "sync", sync_then_report_failure)
    with pytest.raises(OSError, match="post-replace durability error"):
        _cache(runtime, 400).persist(runtime, "session")

    assert image.objects["tensor/session_manifest"] == old_manifest
    reopened = PersistentMachineImage(path)
    restored = Qwen3KVCache.restore(TensorRuntime(reopened), "session", 2)
    assert [item.data for item in restored.keys] == [item.data for item in old_cache.keys]
    assert [item.data for item in restored.values] == [item.data for item in old_cache.values]


def test_manifest_rollback_sync_failure_is_reported(monkeypatch):
    image = PersistentMachineImage()
    runtime = TensorRuntime(image)
    _cache(runtime, 19).persist(runtime, "session")
    original_sync = image.sync
    calls = 0

    def fail_commit_and_rollback():
        nonlocal calls
        calls += 1
        if calls <= 2:
            raise OSError("injected sync failure")
        return original_sync()

    monkeypatch.setattr(image, "sync", fail_commit_and_rollback)
    with pytest.raises(RuntimeError, match="rollback could not be made durable") as exc:
        _cache(runtime, 500).persist(runtime, "session")
    # Tensor writes are staged without sync; these two calls are specifically
    # the manifest commit and the attempted durable rollback.
    assert calls == 2
    assert isinstance(exc.value.__cause__, OSError)


def test_manifest_rollback_directory_fsync_failure_reports_uncertain_durability(monkeypatch, tmp_path):
    import os
    import storage as storage_module

    path = tmp_path / "rollback-directory-fsync.json"
    image = PersistentMachineImage(path)
    runtime = TensorRuntime(image)
    old_cache = _cache(runtime, 23)
    old_cache.persist(runtime, "session")
    old_manifest = image.objects["tensor/session_manifest"]

    original_fsync = storage_module.os.fsync
    fsync_calls = 0

    def fail_commit_and_rollback_directory_fsync(fd):
        nonlocal fsync_calls
        fsync_calls += 1
        # Each sync fsyncs the temporary file, replaces the image, then
        # fsyncs the parent directory. Fail after both replacements so the
        # caller cannot claim either rename was durably confirmed.
        if fsync_calls in (2, 4):
            raise OSError("injected directory fsync failure")
        return original_fsync(fd)

    monkeypatch.setattr(storage_module.os, "fsync", fail_commit_and_rollback_directory_fsync)
    with pytest.raises(RuntimeError, match="rollback could not be made durable") as exc:
        _cache(runtime, 600).persist(runtime, "session")

    assert fsync_calls == 4
    assert isinstance(exc.value.__cause__, OSError)
    assert image.objects["tensor/session_manifest"] == old_manifest

    # The rollback replacement reached the filesystem, although its directory
    # durability could not be confirmed; reopening should still parse the image
    # and select the old, committed generation in this injected scenario.
    reopened = PersistentMachineImage(path)
    restored = Qwen3KVCache.restore(TensorRuntime(reopened), "session", 2)
    assert [item.data for item in restored.keys] == [item.data for item in old_cache.keys]
    assert [item.data for item in restored.values] == [item.data for item in old_cache.values]

@pytest.mark.parametrize(("field", "invalid_value"), [("version", True), ("num_layers", True)])
def test_restore_rejects_boolean_manifest_schema_integers(field, invalid_value):
    image = PersistentMachineImage()
    runtime = TensorRuntime(image)
    cache = Qwen3KVCache.create(1, runtime)
    cache.append(0, _tensor(31), _tensor(41))
    cache.persist(runtime, "session")

    manifest_key = "tensor/session_manifest"
    manifest = json.loads(image.objects[manifest_key].decode("utf-8"))
    manifest[field] = invalid_value
    image.objects[manifest_key] = json.dumps(manifest).encode("utf-8")

    with pytest.raises(ValueError, match="invalid Qwen3 KV cache manifest"):
        Qwen3KVCache.restore(runtime, "session", 1)

def test_persist_rejects_boolean_manifest_version():
    image = PersistentMachineImage()
    runtime = TensorRuntime(image)
    _cache(runtime, 29).persist(runtime, "session")

    manifest_key = "tensor/session_manifest"
    manifest = json.loads(image.objects[manifest_key].decode("utf-8"))
    manifest["version"] = True
    image.objects[manifest_key] = json.dumps(manifest).encode("utf-8")

    with pytest.raises(ValueError, match="invalid Qwen3 KV cache manifest"):
        _cache(runtime, 39).persist(runtime, "session")
