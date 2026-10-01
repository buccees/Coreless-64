from qwen3 import Qwen3Config


def test_qwen3_config_supports_gqa():
    cfg = Qwen3Config(5120, 17408, 64, 64, 8, 151936, 40960)
    assert cfg.resolved_head_dim == 80
    assert cfg.kv_group_size == 8


def test_qwen3_config_rejects_invalid_head_ratio():
    try:
        Qwen3Config(512, 1024, 2, 8, 3, 100, 128)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid GQA ratio was accepted")


from model_weights import ModelTensor, ModelWeights
from tensor import Tensor
from qwen3 import Qwen3KVCache, qwen3_attention


def _identity(size):
    return Tensor.from_values(
        (size, size),
        (1.0 if row == col else 0.0 for row in range(size) for col in range(size)),
    )


def test_qwen3_kv_cache_matches_uncached_attention():
    identity = _identity(2)
    weights = ModelWeights([
        ModelTensor("model.layers.0.self_attn.q_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.k_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.v_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.o_proj.weight", identity),
        ModelTensor(
            "model.layers.0.self_attn.q_norm.weight",
            Tensor.from_values((2,), (1.0, 1.0)),
        ),
        ModelTensor(
            "model.layers.0.self_attn.k_norm.weight",
            Tensor.from_values((2,), (1.0, 1.0)),
        ),
    ])
    cfg = Qwen3Config(2, 4, 1, 1, 1, 8, 16, head_dim=2)
    hidden = Tensor.from_values((2, 2), (1.0, 0.0, 0.0, 1.0))

    uncached = qwen3_attention(hidden, weights, "model.layers.0", cfg)

    cache = Qwen3KVCache.create(1)
    first = qwen3_attention(
        Tensor.from_values((1, 2), (1.0, 0.0)),
        weights, "model.layers.0", cfg, cache,
    )
    second = qwen3_attention(
        Tensor.from_values((1, 2), (0.0, 1.0)),
        weights, "model.layers.0", cfg, cache, position_offset=1,
    )

    assert first.data == uncached.data[:2]
    assert second.data == uncached.data[2:]
    assert cache.sequence_length == 2
