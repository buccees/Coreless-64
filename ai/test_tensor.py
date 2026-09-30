from ai.tensor import Tensor, add, linear, matmul, relu, softmax


def test_tensor_shape_and_indexing():
    tensor = Tensor.from_values((2, 2), [1, 2, 3, 4])
    assert tensor.shape == (2, 2)
    assert tensor.at(0, 1) == 2
    assert tensor.at(1, 0) == 3


def test_matmul():
    a = Tensor.from_values((2, 3), [1, 2, 3, 4, 5, 6])
    b = Tensor.from_values((3, 2), [7, 8, 9, 10, 11, 12])
    assert matmul(a, b).data == (58.0, 64.0, 139.0, 154.0)


def test_linear_and_relu():
    x = Tensor.from_values((1, 2), [2, -1])
    weights = Tensor.from_values((2, 2), [1, 2, 3, 4])
    bias = Tensor.from_values((1, 2), [1, 1])
    assert linear(x, weights, bias).data == (0.0, 1.0)
    assert relu(Tensor.from_values((1, 3), [-1, 2, -3])).data == (0.0, 2.0, 0.0)


def test_softmax_is_normalized():
    result = softmax(Tensor.from_values((3,), [1, 2, 3]))
    assert abs(sum(result.data) - 1.0) < 1e-12
    assert result.data[2] > result.data[1] > result.data[0]


def test_shape_mismatch_rejected():
    a = Tensor.from_values((2,), [1, 2])
    b = Tensor.from_values((3,), [1, 2, 3])
    try:
        add(a, b)
    except ValueError:
        pass
    else:
        raise AssertionError("shape mismatch must fail")
