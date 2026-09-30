"""Reference Transformer block built from Coreless tensor primitives."""

from __future__ import annotations

from math import sqrt
from ai.tensor import Tensor, add, matmul
from ai.transformer import feed_forward, scaled_dot_product_attention


def layer_norm(x: Tensor, epsilon: float = 1e-5) -> Tensor:
    if len(x.shape) != 2:
        raise ValueError("layer_norm requires a rank-2 tensor")
    rows, width = x.shape
    values = []
    for row in range(rows):
        row_values = [x.at(row, col) for col in range(width)]
        mean = sum(row_values) / width
        variance = sum((v - mean) ** 2 for v in row_values) / width
        scale = 1.0 / sqrt(variance + epsilon)
        values.extend((v - mean) * scale for v in row_values)
    return Tensor.from_values(x.shape, values)


def transformer_block(
    x: Tensor,
    query_weight: Tensor,
    key_weight: Tensor,
    value_weight: Tensor,
    output_weight: Tensor,
    ff_in: Tensor,
    ff_out: Tensor,
) -> Tensor:
    """Execute one pre-normalized, single-head Transformer block."""
    normalized = layer_norm(x)
    query = matmul(normalized, query_weight)
    key = matmul(normalized, key_weight)
    value = matmul(normalized, value_weight)
    attention = scaled_dot_product_attention(query, key, value)
    projected = matmul(attention, output_weight)
    residual = add(x, projected)
    return add(residual, feed_forward(layer_norm(residual), ff_in, ff_out))
