from ai.tensor import Tensor
from ai.transformer_block import layer_norm, transformer_block


def test_layer_norm_zero_centers_rows():
    x = Tensor.from_values((2, 3), [1, 2, 3, 2, 4, 6])
    result = layer_norm(x)
    assert abs(sum(result.data[:3])) < 1e-12
    assert abs(sum(result.data[3:])) < 1e-12


def test_transformer_block_preserves_shape():
    x = Tensor.from_values((2, 2), [1, 0, 0, 1])
    identity = Tensor.from_values((2, 2), [1, 0, 0, 1])
    result = transformer_block(
        x, identity, identity, identity, identity, identity, identity
    )
    assert result.shape == x.shape
    assert all(value == value for value in result.data)
