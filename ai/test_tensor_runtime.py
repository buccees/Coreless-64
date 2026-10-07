from ai.tensor import Tensor
from ai.tensor_runtime import TensorRuntime
from storage import PersistentMachineImage


def test_tensor_runtime_executes_core_operations():
    runtime = TensorRuntime()
    left = runtime.create((2, 2), [1, 2, 3, 4])
    right = runtime.create((2, 2), [5, 6, 7, 8])
    assert runtime.add(left, right).data == (6.0, 8.0, 10.0, 12.0)
    assert runtime.matmul(left, right).data == (19.0, 22.0, 43.0, 50.0)
    assert runtime.relu(Tensor.from_values((3,), [-1, 2, -3])).data == (0.0, 2.0, 0.0)


def test_tensor_runtime_persists_tensor_dtype():
    image = PersistentMachineImage()
    runtime = TensorRuntime(image)
    value = Tensor.from_values((2, 2), [1, 2, 3, 4], dtype="bf16")
    key = runtime.save("weights", value)
    image.sync()
    assert key == "tensor/weights"
    restored = TensorRuntime(image).load("weights")
    assert restored.shape == value.shape
    assert restored.dtype == value.dtype
    assert restored.data == value.data


def test_tensor_runtime_executes_bf16_matmul_through_coreless_matrix():
    from core import CorelessCPU

    runtime = TensorRuntime(cpu=CorelessCPU())
    left = runtime.create((2, 2), [1.0, 2.0, 3.0, 4.0], dtype="bf16")
    right = runtime.create((2, 2), [5.0, 6.0, 7.0, 8.0], dtype="bf16")

    result = runtime.matmul(left, right)

    assert result.dtype == "bf16"
    assert result.data == (19.0, 22.0, 43.0, 50.0)


def test_tensor_runtime_executes_fp32_matmul_through_coreless_matrix():
    from core import CorelessCPU

    runtime = TensorRuntime(cpu=CorelessCPU())
    left = runtime.create((2, 2), [1.5, 2.0, 3.0, 4.0], dtype="fp32")
    right = runtime.create((2, 2), [5.0, 6.0, 7.0, 8.0], dtype="fp32")

    result = runtime.matmul(left, right)

    assert result.dtype == "fp32"
    assert result.data == (21.5, 25.0, 43.0, 50.0)


def test_tensor_runtime_tiles_large_bf16_matmul_through_coreless_matrix():
    from core import CorelessCPU

    runtime = TensorRuntime(cpu=CorelessCPU())
    left = runtime.create((17, 17), [1.0] * (17 * 17), dtype="bf16")
    right = runtime.create((17, 17), [1.0] * (17 * 17), dtype="bf16")

    result = runtime.matmul(left, right)

    assert result.shape == (17, 17)
    assert result.dtype == "bf16"
    assert result.data == (17.0,) * (17 * 17)


class TrackingCorelessCPU(__import__("core", fromlist=["CorelessCPU"]).CorelessCPU):
    def __init__(self):
        super().__init__()
        self.vector_boundary_calls = 0
        self.matrix_boundary_calls = 0

    def execute_vector(self, op, rd, rs1, rs2, w1):
        self.vector_boundary_calls += 1
        return super().execute_vector(op, rd, rs1, rs2, w1)

    def execute_matrix(self, op, rd, rs1, rs2, w1, w2, w3):
        self.matrix_boundary_calls += 1
        return super().execute_matrix(op, rd, rs1, rs2, w1, w2, w3)


def test_tensor_runtime_crosses_only_public_coreless_execution_boundaries():
    cpu = TrackingCorelessCPU()
    runtime = TensorRuntime(cpu=cpu)

    left = runtime.create((4,), [1.0, 2.0, 3.0, 4.0], dtype="fp32")
    right = runtime.create((4,), [5.0, 6.0, 7.0, 8.0], dtype="fp32")
    vector_result = runtime.vector_add(left, right)

    matrix_left = runtime.create((2, 2), [1.0, 2.0, 3.0, 4.0], dtype="fp32")
    matrix_right = runtime.create((2, 2), [5.0, 6.0, 7.0, 8.0], dtype="fp32")
    matrix_result = runtime.matmul(matrix_left, matrix_right)

    assert vector_result.data == (6.0, 8.0, 10.0, 12.0)
    assert matrix_result.data == (19.0, 22.0, 43.0, 50.0)
    assert cpu.vector_boundary_calls == 1
    assert cpu.matrix_boundary_calls == 1


def test_tensor_runtime_routes_scalar_multiplication_through_coreless_vector():
    cpu = TrackingCorelessCPU()
    runtime = TensorRuntime(cpu=cpu)

    value = runtime.create((4,), [1.0, 2.0, 3.0, 4.0], dtype="fp32")

    result = runtime.mul_scalar(value, 2.5)

    assert result.data == (2.5, 5.0, 7.5, 10.0)
    assert cpu.vector_boundary_calls == 1


def test_tensor_runtime_broadcasts_rms_scale_through_coreless_vector():
    cpu = TrackingCorelessCPU()
    runtime = TensorRuntime(cpu=cpu)

    value = runtime.create((4,), [1.0, 2.0, 3.0, 4.0], dtype="fp32")
    scale = runtime.create((1,), [2.0], dtype="fp32")

    result = runtime.mul_broadcast(value, scale)

    assert result.data == (2.0, 4.0, 6.0, 8.0)
    assert cpu.vector_boundary_calls == 1


def test_tensor_runtime_transposes_rank2_tensor_at_coreless_boundary():
    runtime = TensorRuntime()
    value = runtime.create((2, 3), [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype="fp32")

    result = runtime.transpose(value)

    assert result.shape == (3, 2)
    assert result.data == (1.0, 4.0, 2.0, 5.0, 3.0, 6.0)


def test_tensor_runtime_native_head_reshape_and_gqa_repeat():
    runtime = TensorRuntime()
    value = runtime.create((2, 4), [1, 2, 3, 4, 5, 6, 7, 8], dtype="fp32")
    heads = runtime.reshape_heads(value, 2, 2)
    assert heads.shape == (2, 2, 2)
    assert heads.data == (1.0, 2.0, 5.0, 6.0, 3.0, 4.0, 7.0, 8.0)
    repeated = runtime.repeat_heads(heads, 2)
    assert repeated.shape == (4, 2, 2)
    assert repeated.data == heads.data[:4] + heads.data[:4] + heads.data[4:] + heads.data[4:]


def test_tensor_runtime_batch_matmul_uses_contiguous_head_storage():
    class CountingTensor:
        def __init__(self, shape, data, dtype="fp32"):
            self.shape = shape
            self.data = tuple(data)
            self.dtype = dtype
            self.at_calls = 0

        def at(self, *indices):
            self.at_calls += 1
            raise AssertionError("batch_matmul should use contiguous head storage")

    runtime = TensorRuntime()
    left = CountingTensor((2, 1, 2), [1.0, 2.0, 3.0, 4.0])
    right = CountingTensor((2, 2, 1), [5.0, 6.0, 7.0, 8.0])

    result = runtime.batch_matmul(left, right)

    assert result.shape == (2, 1, 1)
    assert result.data == (17.0, 53.0)
    assert left.at_calls == 0
    assert right.at_calls == 0


def test_tensor_runtime_batched_attention_matmul():
    runtime = TensorRuntime()
    q = runtime.create((2, 1, 2), [1, 2, 3, 4], dtype="fp32")
    k = runtime.create((2, 2, 2), [5, 6, 7, 8, 1, 0, 0, 1], dtype="fp32")
    result = runtime.batch_matmul(q, runtime.transpose_last_two(k))
    assert result.shape == (2, 1, 2)
    assert result.data == (19.0, 22.0, 7.0, 4.0)


def test_tensor_runtime_softmax_last_dim():
    runtime = TensorRuntime()
    value = runtime.create((2, 2, 2), [1, 2, 2, 1, 0, 0, 1, 3], dtype="fp32")
    result = runtime.softmax_last_dim(value)
    assert result.shape == value.shape
    assert abs(result.at(0, 0, 0) + result.at(0, 0, 1) - 1.0) < 1e-6
    assert abs(result.at(1, 1, 0) + result.at(1, 1, 1) - 1.0) < 1e-6


def test_tensor_runtime_causal_mask_rank3():
    runtime = TensorRuntime()
    mask = runtime.causal_mask((2, 2, 3), query_offset=1, dtype="fp32")
    assert mask.data == (
        1.0, 1.0, 0.0,
        1.0, 1.0, 1.0,
        1.0, 1.0, 0.0,
        1.0, 1.0, 1.0,
    )


def test_tensor_runtime_sum_axis_reduces_attention_heads():
    runtime = TensorRuntime()
    value = runtime.create(
        (2, 2, 2),
        [1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0],
        dtype="fp32",
    )
    result = runtime.sum_axis(value, 0)
    assert result.shape == (2, 2)
    assert result.data == (11.0, 22.0, 33.0, 44.0)


def test_tensor_runtime_rotary_embedding_rank3():
    runtime = TensorRuntime()
    value = runtime.create(
        (1, 2, 4),
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
        dtype="fp32",
    )
    result = runtime.rotary_embedding(value, position_offset=2, theta=10000.0)
    assert result.shape == value.shape
    assert result.data[0:4] != value.data[0:4]
    assert result.data[4:8] != value.data[4:8]




def test_tensor_runtime_rms_norm_heads():
    runtime = TensorRuntime()
    value = runtime.create(
        (2, 1, 2),
        [3.0, 4.0, 1.0, 2.0],
        dtype="fp32",
    )
    weight = runtime.create((2,), [1.0, 2.0], dtype="fp32")
    result = runtime.rms_norm_heads(value, weight, eps=1e-6)
    assert result.shape == value.shape
    assert result.at(0, 0, 0) == 0.6
    assert result.at(0, 0, 1) == 1.6
    assert result.at(1, 0, 0) == 0.6324555320336759
    assert result.at(1, 0, 1) == 1.2649110640673518


def test_tensor_runtime_append_sequence():
    runtime = TensorRuntime()
    existing = runtime.create(
        (2, 2, 2),
        [1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0],
        dtype="fp32",
    )
    update = runtime.create(
        (2, 1, 2),
        [5.0, 6.0, 50.0, 60.0],
        dtype="fp32",
    )
    result = runtime.append_sequence(existing, update)
    assert result.shape == (2, 3, 2)
    assert result.data == (
        1.0, 2.0, 3.0, 4.0, 5.0, 6.0,
        10.0, 20.0, 30.0, 40.0, 50.0, 60.0,
    )


def test_tensor_runtime_grouped_attention_matches_repeated_kv_attention():
    runtime = TensorRuntime()
    q = runtime.create(
        (4, 2, 2),
        [1.0, 0.0, 0.0, 1.0, 2.0, 1.0, 1.0, 2.0,
         1.0, 2.0, 2.0, 1.0, 2.0, 0.0, 0.0, 2.0],
        dtype="fp32",
    )
    k = runtime.create(
        (2, 2, 2),
        [1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 2.0, 0.0],
        dtype="fp32",
    )
    v = runtime.create(
        (2, 2, 2),
        [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        dtype="fp32",
    )
    grouped = runtime.grouped_attention(q, k, v, 2)
    repeated = runtime.attention(q, runtime.repeat_heads(k, 2), runtime.repeat_heads(v, 2))
    assert grouped.shape == repeated.shape
    assert grouped.data == repeated.data


def test_tensor_runtime_grouped_attention_reuses_each_kv_group_once():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.transpose_calls = 0

        def transpose(self, value):
            self.transpose_calls += 1
            return super().transpose(value)

    runtime = RecordingRuntime()
    q = runtime.create((4, 1, 2), [1.0, 0.0, 0.0, 1.0, 2.0, 1.0, 1.0, 2.0], dtype="fp32")
    k = runtime.create((2, 1, 2), [1.0, 0.0, 0.0, 1.0], dtype="fp32")
    v = runtime.create((2, 1, 2), [3.0, 4.0, 5.0, 6.0], dtype="fp32")

    runtime.grouped_attention(q, k, v, 2)

    assert runtime.transpose_calls == 2


def test_tensor_runtime_grouped_attention_uses_contiguous_head_storage():
    class CountingTensor:
        def __init__(self, shape, data, dtype="fp32"):
            self.shape = shape
            self.data = tuple(data)
            self.dtype = dtype
            self.at_calls = 0

        def at(self, *indices):
            self.at_calls += 1
            raise AssertionError("grouped attention should use contiguous head storage")

    runtime = TensorRuntime()
    q = CountingTensor((2, 1, 2), [1.0, 0.0, 0.0, 1.0])
    k = CountingTensor((1, 1, 2), [1.0, 0.0])
    v = CountingTensor((1, 1, 2), [3.0, 4.0])

    result = runtime.grouped_attention(q, k, v, 2)

    assert result.shape == (1, 4)
    assert q.at_calls == 0
    assert k.at_calls == 0
    assert v.at_calls == 0


def test_tensor_runtime_grouped_attention_reuses_causal_mask():
    class RecordingRuntime(TensorRuntime):
        def __init__(self):
            super().__init__()
            self.mask_calls = 0

        def causal_mask(self, shape, query_offset=0, dtype="fp64"):
            self.mask_calls += 1
            return super().causal_mask(shape, query_offset=query_offset, dtype=dtype)

    runtime = RecordingRuntime()
    q = runtime.create((4, 2, 2), [1.0, 0.0, 0.0, 1.0] * 4, dtype="fp32")
    k = runtime.create((2, 2, 2), [1.0, 0.0, 0.0, 1.0] * 2, dtype="fp32")
    v = runtime.create((2, 2, 2), [3.0, 4.0, 5.0, 6.0] * 2, dtype="fp32")

    runtime.grouped_attention(q, k, v, 2)

    assert runtime.mask_calls == 1


def test_tensor_runtime_grouped_attention_rejects_invalid_grouping():
    runtime = TensorRuntime()
    q = runtime.create((3, 1, 2), [1.0, 0.0, 0.0, 1.0, 1.0, 1.0], dtype="fp32")
    k = runtime.create((2, 1, 2), [1.0, 0.0, 0.0, 1.0], dtype="fp32")
    v = runtime.create((2, 1, 2), [1.0, 0.0, 0.0, 1.0], dtype="fp32")
    try:
        runtime.grouped_attention(q, k, v, 2)
    except ValueError as exc:
        assert "query heads must equal key/value heads" in str(exc)
    else:
        raise AssertionError("invalid grouped attention head ratio was accepted")


def test_tensor_runtime_attention():
    runtime = TensorRuntime()
    q = runtime.create((1, 1, 2), [1.0, 2.0], dtype="fp32")
    k = runtime.create((1, 1, 2), [2.0, 1.0], dtype="fp32")
    v = runtime.create((1, 1, 2), [3.0, 4.0], dtype="fp32")
    result = runtime.attention(q, k, v)
    assert result.shape == (1, 2)
    assert result.data == (3.0, 4.0)


def test_tensor_runtime_last_row():
    runtime = TensorRuntime()
    value = runtime.create((3, 2), [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype="fp32")
    result = runtime.last_row(value)
    assert result.shape == (2,)
    assert result.data == (5.0, 6.0)


def test_tensor_runtime_last_row_rejects_non_rank2():
    runtime = TensorRuntime()
    value = runtime.create((2,), [1.0, 2.0], dtype="fp32")
    try:
        runtime.last_row(value)
    except ValueError as exc:
        assert str(exc) == "last_row requires a rank-2 tensor"
    else:
        raise AssertionError("last_row accepted a non-rank-2 tensor")


def test_tensor_runtime_embedding_lookup():
    runtime = TensorRuntime()
    embedding = runtime.create((3, 2), [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype="fp32")
    result = runtime.embedding_lookup(embedding, [2, 0])
    assert result.shape == (2, 2)
    assert result.data == (5.0, 6.0, 1.0, 2.0)


def test_tensor_runtime_rms_norm_rows():
    runtime = TensorRuntime()
    value = runtime.create((2, 2), [3.0, 4.0, 1.0, 2.0], dtype="fp32")
    weight = runtime.create((2,), [1.0, 2.0], dtype="fp32")
    result = runtime.rms_norm_rows(value, weight, eps=1e-6)
    assert result.shape == value.shape
    assert result.data == (0.6, 1.6, 0.6324555320336759, 1.2649110640673518)


def test_tensor_runtime_merges_attention_heads_without_reducing_them():
    runtime = TensorRuntime()
    value = runtime.create(
        (2, 2, 2),
        [1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0],
        dtype="fp32",
    )
    result = runtime.merge_heads(value)
    assert result.shape == (2, 4)
    assert result.data == (1.0, 2.0, 10.0, 20.0, 3.0, 4.0, 30.0, 40.0)



def test_tensor_runtime_head_layout_ops_use_contiguous_storage():
    class CountingTensor:
        def __init__(self, shape, data, dtype="fp32"):
            self.shape = shape
            self.data = tuple(data)
            self.dtype = dtype
            self.at_calls = 0

        def at(self, *indices):
            self.at_calls += 1
            raise AssertionError("head layout operations should use contiguous storage")

    runtime = TensorRuntime()
    value = CountingTensor((2, 2), [1.0, 2.0, 3.0, 4.0])
    heads = runtime.reshape_heads(value, 2, 1)
    assert heads.data == (1.0, 3.0, 2.0, 4.0)
    assert value.at_calls == 0

    repeated = runtime.repeat_heads(
        CountingTensor((2, 2, 1), heads.data),
        2,
    )
    assert repeated.data == (1.0, 3.0, 1.0, 3.0, 2.0, 4.0, 2.0, 4.0)

    transposed = runtime.transpose_last_two(
        CountingTensor((2, 2, 2), [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    )
    assert transposed.data == (1.0, 3.0, 2.0, 4.0, 5.0, 7.0, 6.0, 8.0)


def test_tensor_runtime_transpose_and_merge_use_contiguous_storage():
    class CountingTensor:
        def __init__(self, shape, data, dtype="fp32"):
            self.shape = shape
            self.data = tuple(data)
            self.dtype = dtype
            self.at_calls = 0

        def at(self, *indices):
            self.at_calls += 1
            raise AssertionError("layout transforms should use contiguous storage")

    runtime = TensorRuntime()
    value = CountingTensor((2, 3), [1, 2, 3, 4, 5, 6])
    assert runtime.transpose(value).data == (1.0, 4.0, 2.0, 5.0, 3.0, 6.0)
    assert value.at_calls == 0

    heads = CountingTensor((2, 2, 2), [1, 2, 3, 4, 10, 20, 30, 40])
    result = runtime.merge_heads(heads)
    assert result.data == (1.0, 2.0, 10.0, 20.0, 3.0, 4.0, 30.0, 40.0)
    assert heads.at_calls == 0
