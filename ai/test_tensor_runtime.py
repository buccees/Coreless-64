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


def test_tensor_runtime_persists_tensor():
    image = PersistentMachineImage()
    runtime = TensorRuntime(image)
    value = Tensor.from_values((2, 2), [1, 2, 3, 4])
    key = runtime.save("weights", value)
    image.sync()
    assert key == "tensor/weights"
    restored = TensorRuntime(image).load("weights")
    assert restored.shape == value.shape
    assert restored.data == value.data
