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
