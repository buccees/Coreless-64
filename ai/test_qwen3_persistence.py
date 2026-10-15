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

def test_manifest_sync_failure_rolls_back_published_pointer(monkeypatch):
    image = PersistentMachineImage()
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

