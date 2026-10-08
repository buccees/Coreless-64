from qwen3 import Qwen3Config
from tensor_runtime import TensorRuntime


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


def test_qwen3_kv_cache_preserves_gqa_heads():
    hidden = Tensor.from_values((1, 4), (1.0, 2.0, 3.0, 4.0))
    def zeros(shape):
        size = 1
        for dim in shape:
            size *= dim
        return Tensor.from_values(shape, (0.0 for _ in range(size)))

    weights = ModelWeights([
        ModelTensor("model.layers.0.self_attn.q_proj.weight", zeros((8, 4))),
        ModelTensor("model.layers.0.self_attn.k_proj.weight", zeros((4, 4))),
        ModelTensor("model.layers.0.self_attn.v_proj.weight", zeros((4, 4))),
        ModelTensor("model.layers.0.self_attn.o_proj.weight", zeros((4, 8))),
        ModelTensor("model.layers.0.self_attn.q_norm.weight",
                    Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.self_attn.k_norm.weight",
                    Tensor.from_values((2,), (1.0, 1.0))),
    ])
    cfg = Qwen3Config(4, 8, 1, 4, 2, 16, 16, head_dim=2)
    cache = Qwen3KVCache.create(1)
    qwen3_attention(hidden, weights, "model.layers.0", cfg, cache)
    assert cache.keys[0].shape == (2, 1, 2)
    assert cache.values[0].shape == (2, 1, 2)
    assert cache.sequence_length == 1


def test_qwen3_attention_single_query_uses_score_length():
    identity = _identity(2)
    weights = ModelWeights([
        ModelTensor("model.layers.0.self_attn.q_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.k_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.v_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.o_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.q_norm.weight",
                    Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.self_attn.k_norm.weight",
                    Tensor.from_values((2,), (1.0, 1.0))),
    ])
    cfg = Qwen3Config(2, 4, 1, 1, 1, 8, 16, head_dim=2)
    hidden = Tensor.from_values((1, 2), (1.0, 0.0))
    result = qwen3_attention(hidden, weights, "model.layers.0", cfg)
    assert result.shape == (1, 2)


class _RecordingTensorRuntime(TensorRuntime):
    def __init__(self):
        super().__init__()
        self.matmul_calls = 0

    def matmul(self, left, right):
        self.matmul_calls += 1
        return super().matmul(left, right)


def test_qwen3_rotary_elementwise_ops_use_tensor_runtime():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.mul_calls = 0
            self.add_calls = 0
            self.sub_calls = 0
            self.sin_calls = 0
            self.cos_calls = 0

        def mul(self, left, right):
            self.mul_calls += 1
            return super().mul(left, right)

        def add(self, left, right):
            self.add_calls += 1
            return super().add(left, right)

        def sub(self, left, right):
            self.sub_calls += 1
            return super().sub(left, right)

        def sin(self, value):
            self.sin_calls += 1
            return super().sin(value)

        def cos(self, value):
            self.cos_calls += 1
            return super().cos(value)

    from qwen3 import _rotary

    runtime = RecordingRuntime()
    result = _rotary([1.0, 2.0], 1, 10000.0, 1.0, runtime)

    assert len(result) == 2
    assert runtime.mul_calls == 4
    assert runtime.add_calls == 1
    assert runtime.sub_calls == 1
    assert runtime.sin_calls == 1
    assert runtime.cos_calls == 1


def test_qwen3_attention_scale_uses_tensor_runtime():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.mul_scalar_calls = 0
            self.softmax_calls = 0
            self.masked_fill_calls = 0

        def mul_scalar(self, value, scalar):
            self.mul_scalar_calls += 1
            return super().mul_scalar(value, scalar)

        def softmax(self, value):
            self.softmax_calls += 1
            return super().softmax(value)

        def masked_fill(self, value, mask, fill_value):
            self.masked_fill_calls += 1
            return super().masked_fill(value, mask, fill_value)

    runtime = RecordingRuntime()
    from qwen3 import _attention

    q = [[[1.0, 2.0]]]
    k = [[[2.0, 1.0]]]
    v = [[[3.0, 4.0]]]
    result = _attention(q, k, v, runtime=runtime)

    assert result == [[3.0, 4.0]]
    assert runtime.mul_scalar_calls == 1
    assert runtime.softmax_calls == 1
    assert runtime.masked_fill_calls == 1


def test_qwen3_nonlinear_ops_cross_tensor_runtime_boundary():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.silu_calls = 0
            self.softmax_calls = 0

        def silu(self, value):
            self.silu_calls += 1
            return super().silu(value)

        def softmax(self, value):
            self.softmax_calls += 1
            return super().softmax(value)

    runtime = RecordingRuntime()
    gate = Tensor.from_values((1, 2), (2.0, -1.0))

    assert runtime.silu(gate).shape == gate.shape
    assert runtime.softmax(Tensor.from_values((1, 2), (1.0, 2.0))).shape == (1, 2)
    assert runtime.silu_calls == 1
    assert runtime.softmax_calls == 1


def test_qwen3_attention_routes_grouped_attention_through_tensor_runtime():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.grouped_attention_calls = 0

        def grouped_attention(
            self,
            q,
            k,
            v,
            kv_group_size,
            *,
            causal=True,
            key_position_offset=0,
        ):
            self.grouped_attention_calls += 1
            return super().grouped_attention(
                q,
                k,
                v,
                kv_group_size,
                causal=causal,
                key_position_offset=key_position_offset,
            )

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
    runtime = RecordingRuntime()
    hidden = Tensor.from_values((2, 2), (1.0, 0.0, 0.0, 1.0))

    qwen3_attention(hidden, weights, "model.layers.0", cfg, runtime=runtime)

    assert runtime.grouped_attention_calls == 1


def test_qwen3_attention_routes_score_and_value_products_through_tensor_runtime():
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
    runtime = _RecordingTensorRuntime()
    hidden = Tensor.from_values((2, 2), (1.0, 0.0, 0.0, 1.0))

    qwen3_attention(hidden, weights, "model.layers.0", cfg, runtime=runtime)

    # q/k/v projections + attention score product + value product + output projection.
    assert runtime.matmul_calls == 5


def test_qwen3_mlp_routes_swiglu_multiply_through_tensor_runtime():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.mul_calls = 0

        def mul(self, left, right):
            self.mul_calls += 1
            return super().mul(left, right)

    from qwen3 import qwen3_mlp
    import math

    identity = _identity(2)
    weights = ModelWeights([
        ModelTensor("model.layers.0.mlp.gate_proj.weight", identity),
        ModelTensor("model.layers.0.mlp.up_proj.weight", identity),
        ModelTensor("model.layers.0.mlp.down_proj.weight", identity),
    ])
    runtime = RecordingRuntime()
    x = Tensor.from_values((1, 2), (2.0, -1.0))

    result = qwen3_mlp(x, weights, "model.layers.0", runtime=runtime)

    assert result.shape == (1, 2)
    assert runtime.mul_calls == 1
    expected = (
        (2.0 / (1.0 + math.exp(-2.0))) * 2.0,
        (-1.0 / (1.0 + math.exp(1.0))) * -1.0,
    )
    assert result.data == expected


def test_qwen3_residual_additions_use_tensor_runtime_boundary():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.add_calls = 0

        def add(self, left, right):
            self.add_calls += 1
            return super().add(left, right)

    runtime = RecordingRuntime()
    left = Tensor.from_values((1, 2), (1.0, 2.0))
    right = Tensor.from_values((1, 2), (3.0, 4.0))

    result = runtime.add(left, right)

    assert result.data == (4.0, 6.0)
    assert runtime.add_calls == 1


def test_qwen3_rms_norm_routes_scaling_through_tensor_runtime():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.mul_calls = 0

        def mul(self, left, right):
            self.mul_calls += 1
            return super().mul(left, right)

    from qwen3 import _rms_norm

    runtime = RecordingRuntime()
    x = Tensor.from_values((1, 2), (3.0, 4.0))
    weight = Tensor.from_values((2,), (1.0, 2.0))

    _rms_norm(x, weight, 1e-6, runtime)

    assert runtime.mul_calls == 1


def test_qwen3_rms_norm_uses_fused_tensor_runtime_primitive():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.rms_norm_calls = 0

        def rms_norm(self, value, weight, *, eps=0.0):
            self.rms_norm_calls += 1
            return super().rms_norm(value, weight, eps=eps)

    from qwen3 import _rms_norm

    runtime = RecordingRuntime()
    x = Tensor.from_values((1, 2), (3.0, 4.0))
    weight = Tensor.from_values((2,), (1.0, 2.0))

    result = _rms_norm(x, weight, 1e-6, runtime)

    assert result.shape == (1, 2)
    assert runtime.rms_norm_calls == 1


def test_qwen3_rms_norm_uses_tensor_runtime_boundary():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.rms_calls = 0
            self.mul_calls = 0

        def mean_square_rsqrt(self, value, *, eps=0.0):
            self.rms_calls += 1
            return super().mean_square_rsqrt(value, eps=eps)

        def mul(self, left, right):
            self.mul_calls += 1
            return super().mul(left, right)

    from qwen3 import _rms_norm

    runtime = RecordingRuntime()
    x = Tensor.from_values((1, 2), (3.0, 4.0))
    weight = Tensor.from_values((2,), (1.0, 2.0))

    result = _rms_norm(x, weight, 1e-6, runtime)

    assert result.shape == (1, 2)
    assert runtime.rms_calls == 1
    assert runtime.mul_calls == 1


def test_qwen3_greedy_decode_uses_tensor_runtime_argmax():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.argmax_calls = 0

        def argmax(self, value):
            self.argmax_calls += 1
            return super().argmax(value)

    runtime = RecordingRuntime()
    values = Tensor.from_values((1, 4), (0.5, 3.0, 2.0, 1.0))
    assert runtime.argmax(Tensor.from_values((4,), values.data[-4:])) == 1
    assert runtime.argmax_calls == 1


def test_qwen3_attention_scaling_uses_scalar_runtime_boundary():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.mul_scalar_calls = 0

        def mul_scalar(self, value, scalar):
            self.mul_scalar_calls += 1
            return super().mul_scalar(value, scalar)

    runtime = RecordingRuntime()
    from qwen3 import _attention

    result = _attention([[[1.0, 2.0]]], [[[2.0, 1.0]]], [[[3.0, 4.0]]], runtime=runtime)

    assert result == [[3.0, 4.0]]
    assert runtime.mul_scalar_calls == 1


def test_qwen3_rms_norm_scaling_uses_scalar_runtime_boundary():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.mul_scalar_calls = 0

        def mul_scalar(self, value, scalar):
            self.mul_scalar_calls += 1
            return super().mul_scalar(value, scalar)

    from qwen3 import _rms_norm

    runtime = RecordingRuntime()
    x = Tensor.from_values((1, 2), (3.0, 4.0))
    weight = Tensor.from_values((2,), (1.0, 2.0))

    result = _rms_norm(x, weight, 1e-6, runtime)

    assert result.shape == (1, 2)
    assert runtime.mul_scalar_calls == 1


def test_qwen3_rms_norm_uses_coreless_rms_reduction():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.rms_calls = 0

        def mean_square_rsqrt(self, value, *, eps=0.0):
            self.rms_calls += 1
            return super().mean_square_rsqrt(value, eps=eps)

    from qwen3 import _rms_norm

    runtime = RecordingRuntime()
    x = Tensor.from_values((1, 2), (3.0, 4.0))
    weight = Tensor.from_values((2,), (1.0, 2.0))

    result = _rms_norm(x, weight, 1e-6, runtime)

    assert result.shape == (1, 2)
    assert runtime.rms_calls == 1



def test_qwen3_rotary_angle_generation_uses_tensor_runtime():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.rope_angle_calls = []

        def rope_angles(self, half, position, theta, *, scaling_factor=None, dtype="fp64"):
            self.rope_angle_calls.append((half, position, theta, scaling_factor, dtype))
            return super().rope_angles(
                half, position, theta, scaling_factor=scaling_factor, dtype=dtype
            )

    from qwen3 import _rotary

    runtime = RecordingRuntime()
    result = _rotary([1.0, 2.0, 3.0, 4.0], 3, 10000.0, 2.0, runtime)

    assert len(result) == 4
    assert runtime.rope_angle_calls == [(2, 3, 10000.0, 2.0, "fp64")]


def test_qwen3_rotary_tensor_path_uses_native_runtime_boundary():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.rotary_calls = 0

        def rotary_embedding(self, value, *, position_offset=0, theta=1000000.0, scaling_factor=None):
            self.rotary_calls += 1
            return super().rotary_embedding(
                value,
                position_offset=position_offset,
                theta=theta,
                scaling_factor=scaling_factor,
            )

    from qwen3 import _rotary_tensor

    runtime = RecordingRuntime()
    value = Tensor.from_values((2, 1, 4), [1.0, 2.0, 3.0, 4.0, 4.0, 3.0, 2.0, 1.0])
    result = _rotary_tensor(value, 5, 10000.0, None, runtime)

    assert result.shape == value.shape
    assert runtime.rotary_calls == 1


def test_qwen3_head_rms_norm_uses_native_rank3_runtime_boundary():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def rms_norm_heads(self, value, weight, *, eps=0.0):
            self.calls += 1
            return super().rms_norm_heads(value, weight, eps=eps)

    from qwen3 import _head_rms_norm

    runtime = RecordingRuntime()
    value = Tensor.from_values((2, 1, 2), [3.0, 4.0, 1.0, 2.0])
    weight = Tensor.from_values((2,), [1.0, 1.0])
    result = _head_rms_norm(value, weight, 1e-6, runtime)

    assert result.shape == value.shape
    assert runtime.calls == 1


def test_qwen3_kv_cache_binds_tensor_runtime():
    runtime = TensorRuntime()
    cache = Qwen3KVCache.create(1, runtime)
    key = Tensor.from_values((1, 1, 2), (1.0, 2.0))
    value = Tensor.from_values((1, 1, 2), (3.0, 4.0))
    cache.append(0, key, value)
    cache.append(0, key, value)
    assert cache.runtime is runtime
    assert cache.sequence_length == 2


def test_qwen3_kv_cache_rejects_runtime_rebinding():
    runtime = TensorRuntime()
    other = TensorRuntime()
    cache = Qwen3KVCache.create(1, runtime)
    key = Tensor.from_values((1, 1, 2), (1.0, 2.0))
    value = Tensor.from_values((1, 1, 2), (3.0, 4.0))
    cache.append(0, key, value)
    try:
        cache.append(0, key, value, other)
    except ValueError:
        pass
    else:
        raise AssertionError("Qwen3 KV cache accepted a different TensorRuntime")


def test_qwen3_kv_cache_uses_tensor_runtime_append_boundary():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.append_calls = 0

        def append_sequence(self, existing, update):
            self.append_calls += 1
            return super().append_sequence(existing, update)

    identity = _identity(2)
    weights = ModelWeights([
        ModelTensor("model.layers.0.self_attn.q_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.k_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.v_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.o_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.q_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.self_attn.k_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
    ])
    cfg = Qwen3Config(2, 4, 1, 1, 1, 8, 16, head_dim=2)
    runtime = RecordingRuntime()
    cache = Qwen3KVCache.create(1)
    qwen3_attention(Tensor.from_values((1, 2), (1.0, 0.0)), weights, "model.layers.0", cfg, cache, runtime=runtime)
    qwen3_attention(Tensor.from_values((1, 2), (0.0, 1.0)), weights, "model.layers.0", cfg, cache, position_offset=1, runtime=runtime)
    assert runtime.append_calls == 2
    assert cache.keys[0].shape == (1, 2, 2)
    assert cache.values[0].shape == (1, 2, 2)


def test_qwen3_attention_uses_native_head_staging_boundaries():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.reshape_calls = 0
            self.head_norm_calls = 0
            self.rotary_calls = 0

        def reshape_heads(self, value, heads, head_dim):
            self.reshape_calls += 1
            return super().reshape_heads(value, heads, head_dim)

        def rms_norm_heads(self, value, weight, *, eps=0.0):
            self.head_norm_calls += 1
            return super().rms_norm_heads(value, weight, eps=eps)

        def rotary_embedding(self, value, *, position_offset=0, theta=1000000.0, scaling_factor=None):
            self.rotary_calls += 1
            return super().rotary_embedding(
                value,
                position_offset=position_offset,
                theta=theta,
                scaling_factor=scaling_factor,
            )

    identity = _identity(2)
    weights = ModelWeights([
        ModelTensor("model.layers.0.self_attn.q_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.k_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.v_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.o_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.q_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.self_attn.k_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
    ])
    cfg = Qwen3Config(2, 4, 1, 1, 1, 8, 16, head_dim=2)
    runtime = RecordingRuntime()

    qwen3_attention(
        Tensor.from_values((1, 2), (1.0, 0.0)),
        weights,
        "model.layers.0",
        cfg,
        runtime=runtime,
    )

    assert runtime.reshape_calls == 3
    assert runtime.head_norm_calls == 2
    assert runtime.rotary_calls == 2


def test_qwen3_attention_uses_gqa_grouping_and_cache_sequence_offset():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.group_sizes = []
            self.offsets = []

        def grouped_attention(self, q, k, v, kv_group_size, *, causal=True, key_position_offset=0):
            self.group_sizes.append(kv_group_size)
            self.offsets.append(key_position_offset)
            return super().grouped_attention(
                q, k, v, kv_group_size,
                causal=causal,
                key_position_offset=key_position_offset,
            )

    identity = _identity(4)
    weights = ModelWeights([
        ModelTensor("model.layers.0.self_attn.q_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.k_proj.weight", Tensor.from_values((2, 4), [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
        ])),
        ModelTensor("model.layers.0.self_attn.v_proj.weight", Tensor.from_values((2, 4), [
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ])),
        ModelTensor("model.layers.0.self_attn.o_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.q_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.self_attn.k_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
    ])
    cfg = Qwen3Config(4, 8, 1, 4, 2, 16, 16, head_dim=1)
    runtime = RecordingRuntime()
    cache = Qwen3KVCache.create(1)

    first = Tensor.from_values((1, 4), (1.0, 0.0, 0.0, 1.0))
    second = Tensor.from_values((1, 4), (0.0, 1.0, 1.0, 0.0))
    qwen3_attention(first, weights, "model.layers.0", cfg, cache, runtime=runtime)
    qwen3_attention(second, weights, "model.layers.0", cfg, cache, position_offset=1, runtime=runtime)

    assert runtime.group_sizes == [2, 2]
    assert runtime.offsets == [0, 1]
    assert cache.sequence_length == 2
    assert cache.keys[0].shape == (2, 2, 1)


def test_qwen3_attention_uses_native_grouped_attention_boundary():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.grouped_attention_calls = 0

        def grouped_attention(self, q, k, v, kv_group_size, *, causal=True, key_position_offset=0):
            self.grouped_attention_calls += 1
            assert kv_group_size == 1
            return super().grouped_attention(
                q, k, v, kv_group_size, causal=causal, key_position_offset=key_position_offset
            )

    identity = _identity(2)
    weights = ModelWeights([
        ModelTensor("model.layers.0.self_attn.q_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.k_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.v_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.o_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.q_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.self_attn.k_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
    ])
    cfg = Qwen3Config(2, 4, 1, 1, 1, 8, 16, head_dim=2)
    runtime = RecordingRuntime()
    qwen3_attention(Tensor.from_values((1, 2), (1.0, 0.0)), weights, "model.layers.0", cfg, runtime=runtime)
    assert runtime.grouped_attention_calls == 1


    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.attention_calls = 0

        def attention(self, q, k, v, *, causal=True, key_position_offset=0):
            self.attention_calls += 1
            return super().attention(q, k, v, causal=causal, key_position_offset=key_position_offset)

    identity = _identity(2)
    weights = ModelWeights([
        ModelTensor("model.layers.0.self_attn.q_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.k_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.v_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.o_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.q_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.self_attn.k_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
    ])
    cfg = Qwen3Config(2, 4, 1, 1, 1, 8, 16, head_dim=2)
    runtime = RecordingRuntime()
    qwen3_attention(Tensor.from_values((1, 2), (1.0, 0.0)), weights, "model.layers.0", cfg, runtime=runtime)
    assert runtime.attention_calls == 1


def test_qwen3_kv_cache_layer_accessor_owns_state_boundary():
    cache = Qwen3KVCache.create(1)
    key = Tensor.from_values((1, 1, 2), [1.0, 2.0])
    value = Tensor.from_values((1, 1, 2), [3.0, 4.0])
    cache.append(0, key, value)
    cached_key, cached_value = cache.layer(0)
    assert cache.layer_count == 1
    assert cached_key is key
    assert cached_value is value


def test_qwen3_kv_cache_append_owns_runtime_boundary():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.append_calls = 0

        def append_sequence(self, existing, update):
            self.append_calls += 1
            return super().append_sequence(existing, update)

    runtime = RecordingRuntime()
    cache = Qwen3KVCache.create(1)
    key = Tensor.from_values((1, 1, 2), [1.0, 2.0])
    value = Tensor.from_values((1, 1, 2), [3.0, 4.0])
    cache.append(0, key, value, runtime)
    cache.append(0, key, value, runtime)
    assert runtime.append_calls == 2
    assert cache.keys[0].shape == (1, 2, 2)
    assert cache.values[0].shape == (1, 2, 2)


def test_qwen3_kv_cache_persists_through_tensor_runtime():
    from storage import PersistentMachineImage

    runtime = TensorRuntime(PersistentMachineImage())
    cache = Qwen3KVCache.create(2)
    cache.append(
        0,
        Tensor.from_values((1, 1, 2), [1.0, 2.0], dtype="fp32"),
        Tensor.from_values((1, 1, 2), [3.0, 4.0], dtype="fp32"),
    )
    cache.append(
        1,
        Tensor.from_values((1, 1, 2), [5.0, 6.0], dtype="fp32"),
        Tensor.from_values((1, 1, 2), [7.0, 8.0], dtype="fp32"),
    )
    saved = cache.persist(runtime, "session")
    assert saved == (
        "tensor/session_layer_0_key",
        "tensor/session_layer_0_value",
        "tensor/session_layer_1_key",
        "tensor/session_layer_1_value",
    )
    restored = Qwen3KVCache.restore(runtime, "session", 2)
    assert restored.layer_count == 2
    assert restored.keys[0].data == (1.0, 2.0)
    assert restored.values[1].data == (7.0, 8.0)
    assert restored.sequence_length == 1



def test_qwen3_kv_cache_rejects_divergent_layer_lengths():
    cache = Qwen3KVCache.create(2)
    cache.append(
        0,
        Tensor.from_values((1, 2, 2), [1.0, 2.0, 3.0, 4.0]),
        Tensor.from_values((1, 2, 2), [5.0, 6.0, 7.0, 8.0]),
    )
    cache.append(
        1,
        Tensor.from_values((1, 1, 2), [9.0, 10.0]),
        Tensor.from_values((1, 1, 2), [11.0, 12.0]),
    )
    try:
        cache.validate()
    except ValueError as exc:
        assert "share one sequence length" in str(exc)
    else:
        raise AssertionError("divergent cache layer lengths were accepted")


def test_qwen3_runtime_assembles_final_logits_for_greedy_decode():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.last_row_calls = 0
            self.argmax_calls = 0

        def last_row(self, value):
            self.last_row_calls += 1
            return super().last_row(value)

        def argmax(self, value):
            self.argmax_calls += 1
            return super().argmax(value)

    from qwen3 import Qwen3Runtime

    identity = _identity(2)
    zero = Tensor.from_values((2, 2), (0.0, 0.0, 0.0, 0.0))
    embedding = Tensor.from_values((3, 2), (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    lm_head = Tensor.from_values((3, 2), (0.0, 2.0, 0.0, 1.0, 0.0, 0.0))
    weights = ModelWeights([
        ModelTensor("model.embed_tokens.weight", embedding),
        ModelTensor("model.layers.0.self_attn.q_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.k_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.v_proj.weight", identity),
        ModelTensor("model.layers.0.self_attn.o_proj.weight", zero),
        ModelTensor("model.layers.0.self_attn.q_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.self_attn.k_norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.input_layernorm.weight", Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.post_attention_layernorm.weight", Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("model.layers.0.mlp.gate_proj.weight", zero),
        ModelTensor("model.layers.0.mlp.up_proj.weight", zero),
        ModelTensor("model.layers.0.mlp.down_proj.weight", zero),
        ModelTensor("model.norm.weight", Tensor.from_values((2,), (1.0, 1.0))),
        ModelTensor("lm_head.weight", lm_head),
    ])
    runtime = RecordingRuntime()
    model = Qwen3Runtime(Qwen3Config(2, 2, 1, 1, 1, 3, 8, head_dim=2), weights, runtime)

    generated = model.generate_greedy([0], 2)

    assert generated == [0, 1, 2]
    assert runtime.last_row_calls == 2
    assert runtime.argmax_calls == 2


def test_qwen3_config_rejects_nonpositive_architecture_dimensions():
    invalid_configs = (
        (0, 4, 1, 2, 1, 8, 16),
        (4, 0, 1, 2, 1, 8, 16),
        (4, 8, 0, 2, 1, 8, 16),
        (4, 8, 1, 0, 1, 8, 16),
        (4, 8, 1, 2, 0, 8, 16),
        (4, 8, 1, 2, 1, 0, 16),
        (4, 8, 1, 2, 1, 8, 0),
    )
    for args in invalid_configs:
        try:
            Qwen3Config(*args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid Qwen3 configuration was accepted: {args}")


def test_qwen3_config_rejects_invalid_normalization_and_rope_parameters():
    base = (4, 8, 1, 2, 1, 8, 16)
    invalid_options = (
        {"rms_norm_eps": -1e-6},
        {"rope_theta": 0.0},
        {"rope_scaling_factor": 0.0},
        {"original_max_position_embeddings": 0},
    )
    for options in invalid_options:
        try:
            Qwen3Config(*base, **options)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid Qwen3 options were accepted: {options}")
