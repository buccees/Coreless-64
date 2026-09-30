from ai.tensor import Tensor
from ai.transformer import feed_forward, scaled_dot_product_attention, transpose


def test_transpose():
    x = Tensor.from_values((2, 3), [1, 2, 3, 4, 5, 6])
    assert transpose(x).data == (1.0, 4.0, 2.0, 5.0, 3.0, 6.0)


def test_scaled_dot_product_attention():
    q = Tensor.from_values((1, 2), [1, 0])
    k = Tensor.from_values((2, 2), [1, 0, 0, 1])
    v = Tensor.from_values((2, 2), [10, 0, 0, 20])
    result = scaled_dot_product_attention(q, k, v)
    assert result.shape == (1, 2)
    assert result.data[0] > result.data[1] * 0.25
    assert abs(sum(result.data) - 10.0 * (result.data[0] / 10.0) - 20.0 * (result.data[1] / 20.0)) < 1e-12


def test_feed_forward():
    x = Tensor.from_values((1, 2), [1, 2])
    w_in = Tensor.from_values((2, 2), [1, 0, 0, 1])
    w_out = Tensor.from_values((2, 2), [2, 0, 0, 3])
    result = feed_forward(x, w_in, w_out)
    assert result.data == (2.0, 6.0)
