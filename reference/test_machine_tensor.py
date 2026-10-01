from ai.tensor import Tensor
from pathlib import Path
from reference.machine_runtime import CorelessMachine


def test_machine_exposes_native_tensor_runtime():
    machine = CorelessMachine()
    left = machine.tensor_runtime.create((1, 2), [2, 3])
    right = machine.tensor_runtime.create((2, 1), [4, 5])
    result = machine.tensor_runtime.matmul(left, right)
    assert result.shape == (1, 1)
    assert result.data == (23.0,)


def test_machine_tensor_state_survives_reopen(tmp_path: Path):
    image_path = tmp_path / "coreless.img"
    machine = CorelessMachine(storage_path=image_path)
    value = Tensor.from_values((2,), [7, 11])
    machine.tensor_runtime.save("persistent", value)
    machine.storage.sync()

    reopened = CorelessMachine(storage_path=image_path)
    restored = reopened.tensor_runtime.load("persistent")
    assert restored.shape == value.shape
    assert restored.data == value.data


def test_machine_tensor_runtime_uses_coreless_vector_execution():
    machine = CorelessMachine()
    left = Tensor.from_values((4,), [1, 2, 3, 4], dtype="int32")
    right = Tensor.from_values((4,), [5, 6, 7, 8], dtype="int32")
    assert machine.tensor_runtime.vector_add(left, right).data == (6.0, 8.0, 10.0, 12.0)
    assert machine.tensor_runtime.vector_mul(left, right).data == (5.0, 12.0, 21.0, 32.0)


def test_machine_tensor_runtime_uses_coreless_matrix_execution():
    machine = CorelessMachine()
    left = Tensor.from_values((2, 2), [1, 2, 3, 4], dtype="int8")
    right = Tensor.from_values((2, 2), [5, 6, 7, 8], dtype="int8")
    result = machine.tensor_runtime.matrix_matmul(left, right)
    assert result.shape == (2, 2)
    assert result.dtype == "int8"
    assert result.data == (19.0, 22.0, 43.0, 50.0)
