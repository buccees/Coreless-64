"""Native Qwen3 architecture boundary for Coreless.

This module implements the architecture-specific math needed to execute Qwen3
without converting it into a different model family. It is deliberately
framework-free and keeps the model's GQA, RoPE, RMSNorm, and gated SwiGLU
semantics explicit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass
class Qwen3KVCache:
    """Per-layer native Q/K cache used by autoregressive generation."""
    keys: list[list[list[float]]]
    values: list[list[list[float]]]

    @classmethod
    def create(cls, num_layers: int) -> "Qwen3KVCache":
        return cls([[] for _ in range(num_layers)], [[] for _ in range(num_layers)])

    @property
    def sequence_length(self) -> int:
        return len(self.keys[0]) if self.keys else 0

from .model_weights import ModelWeights
from .tensor import Tensor, add, matmul, softmax


@dataclass(frozen=True)
class Qwen3Config:
    hidden_size: int
    intermediate_size: int
    num_hidden_layers: int
    num_attention_heads: int
    num_key_value_heads: int
    vocab_size: int
    max_position_embeddings: int
    rms_norm_eps: float = 1e-6
    head_dim: int | None = None
    rope_theta: float = 1000000.0
    rope_scaling_factor: float | None = None
    original_max_position_embeddings: int | None = None

    def __post_init__(self) -> None:
        head_dim = self.head_dim or (self.hidden_size // self.num_attention_heads)
        if self.hidden_size % self.num_attention_heads:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        if self.num_attention_heads % self.num_key_value_heads:
            raise ValueError("attention heads must be divisible by key/value heads")
        if head_dim <= 0 or self.num_key_value_heads <= 0:
            raise ValueError("Qwen3 head dimensions must be positive")

    @property
    def resolved_head_dim(self) -> int:
        return self.head_dim or self.hidden_size // self.num_attention_heads

    @property
    def kv_group_size(self) -> int:
        return self.num_attention_heads // self.num_key_value_heads


def _transpose(x: Tensor) -> Tensor:
    rows, cols = x.shape
    return Tensor.from_values((cols, rows),
                              (x.at(r, c) for c in range(cols) for r in range(rows)))


def _reshape_heads(x: Tensor, heads: int, head_dim: int) -> list[list[list[float]]]:
    if x.shape[1] != heads * head_dim:
        raise ValueError("projection shape does not match Qwen3 head dimensions")
    return [
        [x.data[(pos * heads + head) * head_dim:
                 (pos * heads + head + 1) * head_dim]
         for pos in range(x.shape[0])]
        for head in range(heads)
    ]


def _rotary(head: list[float], position: int, theta: float, scaling_factor: float | None = None) -> list[float]:
    out = head[:]
    half = len(head) // 2
    for i in range(half):
        inv = theta ** (-2.0 * i / len(head))
        angle = position * inv\n        if scaling_factor is not None and scaling_factor > 1.0:\n            angle /= scaling_factor
        c, s = math.cos(angle), math.sin(angle)
        a, b = head[i], head[i + half]
        out[i] = a * c - b * s
        out[i + half] = a * s + b * c
    return out


def _repeat_kv(heads: list[list[list[float]]], repeats: int) -> list[list[list[float]]]:
    return [head for head in heads for _ in range(repeats)]


def _attention(q, k, v, causal=True, key_position_offset=0) -> list[list[float]]:
    query_positions = len(q[0])
    key_positions = len(k[0])
    dim = len(q[0][0])
    output = [[0.0] * dim for _ in range(query_positions)]
    scale = 1.0 / math.sqrt(dim)
    for head in range(len(q)):
        for row in range(query_positions):
            scores = []
            absolute_query_position = key_position_offset + row
            for col in range(key_positions):
                scores.append(sum(q[head][row][i] * k[head][col][i] for i in range(dim))
                              * scale if (not causal or col <= absolute_query_position) else float("-inf"))
            weights = softmax(Tensor.from_values((positions,), scores)).data
            for col, weight in enumerate(weights):
                for i in range(dim):
                    output[row][i] += weight * v[head][col][i]
    return output


def _heads_to_tensor(heads: list[list[list[float]]]) -> Tensor:
    positions = len(heads[0])
    flat = []
    for pos in range(positions):
        for head in heads:
            flat.extend(head[pos])
    return Tensor.from_values((positions, len(flat) // positions), flat)


def _rms_norm(x: Tensor, weight: Tensor, eps: float) -> Tensor:
    hidden = x.shape[1]
    rows = []
    for row in range(x.shape[0]):
        chunk = x.data[row * hidden:(row + 1) * hidden]
        scale = (sum(v * v for v in chunk) / hidden + eps) ** -0.5
        rows.extend(v * scale * weight.data[i] for i, v in enumerate(chunk))
    return Tensor.from_values(x.shape, rows)


def _linear(x: Tensor, weight: Tensor) -> Tensor:
    """Apply a Hugging Face Linear weight stored as [out_features, in_features]."""
    return matmul(x, _transpose(weight))


def _apply_head_norm(heads: list[list[list[float]]], weight: Tensor, eps: float) -> list[list[list[float]]]:
    return [
        [
            list(_rms_norm(Tensor.from_values((1, len(values)), values), weight, eps).data)
            for values in head
        ]
        for head in heads
    ]


def qwen3_attention(
    x: Tensor,
    weights: ModelWeights,
    prefix: str,
    cfg: Qwen3Config,
    cache: Qwen3KVCache | None = None,
    position_offset: int = 0,
) -> Tensor:
    q = _linear(x, weights.get(f"{prefix}.self_attn.q_proj.weight"))
    k = _linear(x, weights.get(f"{prefix}.self_attn.k_proj.weight"))
    v = _linear(x, weights.get(f"{prefix}.self_attn.v_proj.weight"))
    qh = _reshape_heads(q, cfg.num_attention_heads, cfg.resolved_head_dim)
    kh = _reshape_heads(k, cfg.num_key_value_heads, cfg.resolved_head_dim)
    vh = _reshape_heads(v, cfg.num_key_value_heads, cfg.resolved_head_dim)
    qh = _apply_head_norm(qh, weights.get(f"{prefix}.self_attn.q_norm.weight"), cfg.rms_norm_eps)
    kh = _apply_head_norm(kh, weights.get(f"{prefix}.self_attn.k_norm.weight"), cfg.rms_norm_eps)
    qh = [[_rotary(h, position_offset + p, cfg.rope_theta, cfg.rope_scaling_factor)
           for p, h in enumerate(head)] for head in qh]
    kh = [[_rotary(h, position_offset + p, cfg.rope_theta, cfg.rope_scaling_factor)
           for p, h in enumerate(head)] for head in kh]

    if cache is not None:
        layer_index = int(prefix.rsplit(".", 1)[-1])
        cache.keys[layer_index].extend(kh)
        cache.values[layer_index].extend(vh)
        kh = cache.keys[layer_index]
        vh = cache.values[layer_index]

    kh = _repeat_kv(kh, cfg.kv_group_size)
    vh = _repeat_kv(vh, cfg.kv_group_size)
    attended = _heads_to_tensor(_attention(
        qh, kh, vh, key_position_offset=position_offset
    ))
    return _linear(attended, weights.get(f"{prefix}.self_attn.o_proj.weight"))


def qwen3_mlp(x: Tensor, weights: ModelWeights, prefix: str) -> Tensor:
    gate = _linear(x, weights.get(f"{prefix}.mlp.gate_proj.weight"))
    up = _linear(x, weights.get(f"{prefix}.mlp.up_proj.weight"))
    gated = Tensor.from_values(gate.shape, (
        (g / (1.0 + math.exp(-g))) * u for g, u in zip(gate.data, up.data)
    ))
    return _linear(gated, weights.get(f"{prefix}.mlp.down_proj.weight"))


class Qwen3Runtime:
    """Native reference runtime for the dense Qwen3 architecture."""

    def __init__(self, config: Qwen3Config, weights: ModelWeights) -> None:
        self.config = config
        self.weights = weights

    def forward(
        self,
        token_ids: Sequence[int],
        cache: Qwen3KVCache | None = None,
    ) -> Tensor:
        if not token_ids:
            raise ValueError("token sequence must not be empty")
        position_offset = cache.sequence_length if cache is not None else 0
        if position_offset + len(token_ids) > self.config.max_position_embeddings:
            raise ValueError("token sequence exceeds Qwen3 context length")
        if cache is not None and len(cache.keys) != self.config.num_hidden_layers:
            raise ValueError("Qwen3 KV cache layer count does not match the model")

        embedding = self.weights.get("model.embed_tokens.weight")
        hidden = Tensor.from_values(
            (len(token_ids), self.config.hidden_size),
            (v for token_id in token_ids
             for v in embedding.data[token_id * self.config.hidden_size:
                                     (token_id + 1) * self.config.hidden_size])
        )
        for layer in range(self.config.num_hidden_layers):
            prefix = f"model.layers.{layer}"
            normed = _rms_norm(hidden, self.weights.get(f"{prefix}.input_layernorm.weight"),
                               self.config.rms_norm_eps)
            hidden = add(hidden, qwen3_attention(
                normed, self.weights, prefix, self.config, cache, position_offset
            ))
            normed = _rms_norm(hidden, self.weights.get(f"{prefix}.post_attention_layernorm.weight"),
                               self.config.rms_norm_eps)
            hidden = add(hidden, qwen3_mlp(normed, self.weights, prefix))
        hidden = _rms_norm(hidden, self.weights.get("model.norm.weight"), self.config.rms_norm_eps)
        lm_head = self.weights.get("lm_head.weight") if self.weights.contains("lm_head.weight") else embedding
        return _linear(hidden, lm_head)
