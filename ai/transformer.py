"""Dependency-free Transformer primitives for Coreless.

The implementation is a deterministic reference layer above ai.tensor. It
establishes the execution contract before optimized/native vector-matrix
kernels are introduced.
"""

from __future__ import annotations

from math import sqrt
from ai.tensor import Tensor, add, matmul, softmax


def transpose(matrix: Tensor) -> Tensor:
    if len(matrix.shape) != 2:
        raise ValueError("transpose requires a rank-2 tensor")
    rows, cols = matrix.shape
    return Tensor.from_values(
        (cols, rows),
        (matrix.at(r, c) for c in range(cols) for r in range(rows)),
    )


def scaled_dot_product_attention(
    query: Tensor,
    key: Tensor,
    value: Tensor,
    scale: float | None = None,
) -> Tensor:
    """Compute single-head attention for [sequence, features] tensors."""
    if any(len(t.shape) != 2 for t in (query, key, value)):
        raise ValueError("attention inputs must be rank-2 tensors")
    if query.shape[1] != key.shape[1]:
        raise ValueError("query/key feature dimensions must match")
    if key.shape[0] != value.shape[0]:
        raise ValueError("key/value sequence dimensions must match")

    factor = scale if scale is not None else 1.0 / sqrt(query.shape[1])
    scores = matmul(query, transpose(key)).map(lambda x: x * factor)

    rows, cols = scores.shape
    weights = []
    for row in range(rows):
        weights.extend(
            softmax(
                Tensor.from_values(
                    (cols,), (scores.at(row, col) for col in range(cols))
                )
            ).data
        )
    return matmul(Tensor.from_values(scores.shape, weights), value)


def feed_forward(
    x: Tensor,
    weight_in: Tensor,
    weight_out: Tensor,
    bias_in: Tensor | None = None,
    bias_out: Tensor | None = None,
) -> Tensor:
    hidden = matmul(x, weight_in)
    if bias_in is not None:
        hidden = add(hidden, bias_in)
    hidden = hidden.map(lambda v: v if v > 0 else 0.0)
    output = matmul(hidden, weight_out)
    if bias_out is not None:
        output = add(output, bias_out)
    return output
