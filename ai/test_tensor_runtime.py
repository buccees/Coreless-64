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
