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
    assert len(cache.keys[0]) == 2
    assert len(cache.values[0]) == 2
    assert all(len(head) == 1 for head in cache.keys[0])
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
            self.mul_calls = 0
            self.softmax_calls = 0
            self.masked_fill_calls = 0

        def mul(self, left, right):
            self.mul_calls += 1
            return super().mul(left, right)

        def softmax(self, value):
            self.softmax_calls += 1
            return super().softmax(value)

        def masked_fill(self, value, mask, fill_value):
            self.masked_fill_calls += 1
            return super().masked_fill(value, mask, fill_value)

    runtime = RecordingRuntime()
    from .qwen3 import _attention

    q = [[[1.0, 2.0]]]
    k = [[[2.0, 1.0]]]
    v = [[[3.0, 4.0]]]
    result = _attention(q, k, v, runtime=runtime)

    assert result == [[3.0, 4.0]]
    assert runtime.mul_calls == 1
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
