from ai.tensor import Tensor
from reference.machine_runtime import CorelessMachine


def test_machine_exposes_native_tensor_runtime():
    machine = CorelessMachine()
    left = machine.tensor_runtime.create((1, 2), [2, 3])
    right = machine.tensor_runtime.create((2, 1), [4, 5])
    result = machine.tensor_runtime.matmul(left, right)
    assert result.shape == (1, 1)
    assert result.data == (23.0,)


def test_machine_tensor_state_survives_reopen():
    machine = CorelessMachine()
    value = Tensor.from_values((2,), [7, 11])
    machine.tensor_runtime.save("persistent", value)
    machine.storage.sync()

    reopened = CorelessMachine(storage_path=machine.storage.path)
    restored = reopened.tensor_runtime.load("persistent")
    assert restored.shape == value.shape
    assert restored.data == value.data
