"""Dependency-free Transformer execution for Coreless.

This is the reference decoder-only execution layer above ai.tensor. External
model formats are translated into ModelWeights; this module executes only the
Coreless-native tensor contract and can later be replaced kernel-for-kernel by
native vector/matrix implementations.
"""

from __future__ import annotations

from math import sqrt
from typing import Sequence

from .model_architecture import TransformerConfig
from .model_weights import ModelWeights
from .tensor import Tensor, add, matmul, softmax


def transpose(matrix: Tensor) -> Tensor:
    if len(matrix.shape) != 2:
        raise ValueError("transpose requires a rank-2 tensor")
    rows, cols = matrix.shape
    return Tensor.from_values(
        (cols, rows),
        (matrix.at(r, c) for c in range(cols) for r in range(rows)),
    )


def embedding(token_ids: Sequence[int], weights: Tensor) -> Tensor:
    if len(weights.shape) != 2:
        raise ValueError("embedding weights must be rank-2")
    vocab, hidden = weights.shape
    if not token_ids:
        raise ValueError("token sequence must not be empty")
    rows = []
    for token_id in token_ids:
        if not 0 <= token_id < vocab:
            raise ValueError("token id is outside vocabulary")
        rows.extend(weights.data[token_id * hidden:(token_id + 1) * hidden])
    return Tensor.from_values((len(token_ids), hidden), rows)


def rms_norm(x: Tensor, weight: Tensor, eps: float = 1e-6) -> Tensor:
    if len(x.shape) != 2 or weight.shape != (x.shape[1],):
        raise ValueError("rms_norm expects [sequence, hidden] and [hidden]")
    hidden = x.shape[1]
    values = []
    for row in range(x.shape[0]):
        start = row * hidden
        chunk = x.data[start:start + hidden]
        scale = (sum(v * v for v in chunk) / hidden + eps) ** -0.5
        values.extend(v * scale * weight.data[i] for i, v in enumerate(chunk))
    return Tensor.from_values(x.shape, values)


def scaled_dot_product_attention(
    query: Tensor,
    key: Tensor,
    value: Tensor,
    scale: float | None = None,
    *,
    causal: bool = False,
) -> Tensor:
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
        row_scores = [
            scores.at(row, col)
            if not causal or col <= row
            else float("-inf")
            for col in range(cols)
        ]
        weights.extend(softmax(Tensor.from_values((cols,), row_scores)).data)
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


def transformer_layer(x: Tensor, weights: ModelWeights, prefix: str) -> Tensor:
    normed = rms_norm(x, weights.get(f"{prefix}.input_norm"))
    q = matmul(normed, weights.get(f"{prefix}.q_proj"))
    k = matmul(normed, weights.get(f"{prefix}.k_proj"))
    v = matmul(normed, weights.get(f"{prefix}.v_proj"))
    attended = matmul(
        scaled_dot_product_attention(q, k, v, causal=True),
        weights.get(f"{prefix}.o_proj"),
    )
    residual = add(x, attended)
    post = rms_norm(residual, weights.get(f"{prefix}.post_norm"))
    ff = feed_forward(
        post,
        weights.get(f"{prefix}.ffn_up"),
        weights.get(f"{prefix}.ffn_down"),
    )
    return add(residual, ff)


class TransformerRuntime:
    """Execute a decoder-only Transformer from Coreless-native tensors."""

    def __init__(self, config: TransformerConfig, weights: ModelWeights) -> None:
        self.config = config
        self.weights = weights

    def forward(self, token_ids: Sequence[int]) -> Tensor:
        if not token_ids:
            raise ValueError("token sequence must not be empty")
        if len(token_ids) > self.config.max_sequence_length:
            raise ValueError("token sequence exceeds model context length")

        hidden = embedding(token_ids, self.weights.get("embedding"))
        if hidden.shape[1] != self.config.hidden_size:
            raise ValueError("embedding hidden size does not match model config")

        for layer in range(self.config.num_layers):
            hidden = transformer_layer(
                hidden, self.weights, f"layers.{layer}"
            )

        hidden = rms_norm(hidden, self.weights.get("final_norm"))
        logits = matmul(hidden, transpose(self.weights.get("lm_head")))
        if logits.shape[1] != self.config.vocab_size:
            raise ValueError("lm_head output size does not match vocabulary")
        return logits

    def next_token_logits(self, token_ids: Sequence[int]) -> Tensor:
        """Return final-position logits as a [vocab] tensor."""
        logits = self.forward(token_ids)
        start = (logits.shape[0] - 1) * logits.shape[1]
        return Tensor.from_values((logits.shape[1],), logits.data[start:])
