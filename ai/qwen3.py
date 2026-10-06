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

from .model_weights import ModelWeights
from .tensor import Tensor, add, matmul, softmax
from .tensor_runtime import TensorRuntime


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
        if not self.keys or not self.keys[0]:
            return 0
        return len(self.keys[0][0])


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
    return Tensor.from_values(
        (cols, rows),
        (x.at(r, c) for c in range(cols) for r in range(rows)),
    )


def _reshape_heads(x: Tensor, heads: int, head_dim: int) -> list[list[list[float]]]:
    if x.shape[1] != heads * head_dim:
        raise ValueError("projection shape does not match Qwen3 head dimensions")
    return [
        [
            x.data[(pos * heads + head) * head_dim:
                   (pos * heads + head + 1) * head_dim]
            for pos in range(x.shape[0])
        ]
        for head in range(heads)
    ]


def _rotary(
    head: list[float],
    position: int,
    theta: float,
    scaling_factor: float | None = None,
    runtime: TensorRuntime | None = None,
) -> list[float]:
    half = len(head) // 2
    if runtime is None:
        out = head[:]
        for i in range(half):
            inv = theta ** (-2.0 * i / len(head))
            angle = position * inv
            if scaling_factor is not None and scaling_factor > 1.0:
                angle /= scaling_factor
            c, s = math.cos(angle), math.sin(angle)
            a, b = head[i], head[i + half]
            out[i] = a * c - b * s
            out[i + half] = a * s + b * c
        return out

    a = Tensor.from_values((half,), head[:half], dtype="fp64")
    b = Tensor.from_values((half,), head[half:], dtype="fp64")
    cosines, sines = [], []
    for i in range(half):
        inv = theta ** (-2.0 * i / len(head))
        angle = position * inv
        if scaling_factor is not None and scaling_factor > 1.0:
            angle /= scaling_factor
        cosines.append(math.cos(angle))
        sines.append(math.sin(angle))
    c = Tensor.from_values((half,), cosines, dtype="fp64")
    s = Tensor.from_values((half,), sines, dtype="fp64")
    ac = runtime.mul(a, c)
    bs = runtime.mul(b, s)
    as_ = runtime.mul(a, s)
    bc = runtime.mul(b, c)
    first = runtime.sub(ac, bs)
    second = runtime.add(as_, bc)
    return list(first.data) + list(second.data)


def _repeat_kv(heads: list[list[list[float]]], repeats: int) -> list[list[list[float]]]:
    return [head for head in heads for _ in range(repeats)]


def _attention(
    q,
    k,
    v,
    causal=True,
    key_position_offset=0,
    runtime: TensorRuntime | None = None,
) -> list[list[float]]:
    """Execute attention score/value products through the Coreless tensor boundary."""
    query_positions = len(q[0])
    key_positions = len(k[0])
    dim = len(q[0][0])
    output = [[0.0] * dim for _ in range(query_positions)]
    scale = 1.0 / math.sqrt(dim)
    multiply = runtime.matmul if runtime is not None else matmul
    for head in range(len(q)):
        query = Tensor.from_values(
            (query_positions, dim),
            (value for row in q[head] for value in row),
        )
        key = Tensor.from_values(
            (key_positions, dim),
            (value for row in k[head] for value in row),
        )
        value = Tensor.from_values(
            (key_positions, dim),
            (value for row in v[head] for value in row),
        )
        scores = multiply(query, _transpose(key))
        if runtime is not None:
            scale_tensor = Tensor.from_values(
                scores.shape,
                (scale for _ in scores.data),
                dtype=scores.dtype,
            )
            scores = runtime.mul(scores, scale_tensor)
        else:
            scores = scores.map(lambda x: x * scale)
        for row in range(query_positions):
            row_scores = [scores.at(row, col) for col in range(key_positions)]
            score_tensor = Tensor.from_values((1, key_positions), row_scores)
            if causal:
                mask = Tensor.from_values(
                    score_tensor.shape,
                    (
                        1.0 if col <= key_position_offset + row else 0.0
                        for col in range(key_positions)
                    ),
                    dtype=score_tensor.dtype,
                )
                score_tensor = (
                    runtime.masked_fill(score_tensor, mask, float("-inf"))
                    if runtime is not None
                    else Tensor.from_values(
                        score_tensor.shape,
                        (value if mask_value else float("-inf")
                        for value, mask_value in zip(score_tensor.data, mask.data)
                    )
                )
            weights = runtime.softmax(score_tensor) if runtime is not None else softmax(score_tensor)
            attended = multiply(weights, value)
            for i, item in enumerate(attended.data):
                output[row][i] += item
    return output


def _heads_to_tensor(heads: list[list[list[float]]]) -> Tensor:
    positions = len(heads[0])
    flat = []
    for pos in range(positions):
        for head in heads:
            flat.extend(head[pos])
    return Tensor.from_values((positions, len(flat) // positions), flat)


def _rms_norm(
    x: Tensor,
    weight: Tensor,
    eps: float,
    runtime: TensorRuntime | None = None,
) -> Tensor:
    hidden = x.shape[1]
    rows = []
    for row in range(x.shape[0]):
        chunk = Tensor.from_values(
            (hidden,),
            x.data[row * hidden:(row + 1) * hidden],
            dtype=x.dtype,
        )
            squared = (
            runtime.dot(chunk, chunk)
            if runtime is not None
            else sum(v * v for v in chunk.data)
        ) / hidden
        scale = (
            runtime.rsqrt(Tensor.from_values((1,), [squared], dtype=x.dtype), eps=eps).data[0]
            if runtime is not None
            else (squared + eps) ** -0.5
        )
        scale_tensor = Tensor.from_values(
            (hidden,),
            (scale for _ in range(hidden)),
            dtype=x.dtype,
        )
        scaled = (
            runtime.mul(chunk, scale_tensor)
            if runtime is not None
            else Tensor.from_values(
                (hidden,),
                (v * scale for v in chunk.data),
                dtype=x.dtype,
            )
        )
        weighted = (
            runtime.mul(scaled, weight)
            if runtime is not None
            else Tensor.from_values(x.shape[1:], (v * w for v, w in zip(scaled.data, weight.data)), dtype=x.dtype)
        )
        rows.extend(weighted.data)
    return Tensor.from_values(x.shape, rows, dtype=x.dtype)


def _linear(
    x: Tensor,
    weight: Tensor,
    runtime: TensorRuntime | None = None,
) -> Tensor:
    """Apply a Hugging Face Linear weight through the Coreless tensor boundary."""
    multiply = runtime.matmul if runtime is not None else matmul
    return multiply(x, _transpose(weight))


def _apply_head_norm(
    heads: list[list[list[float]]],
    weight: Tensor,
    eps: float,
    runtime: TensorRuntime | None = None,
) -> list[list[list[float]]]:
    return [
        [
            list(
                _rms_norm(
                    Tensor.from_values((1, len(values)), values),
                    weight,
                    eps,
                    runtime,
                ).data
            )
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
    runtime: TensorRuntime | None = None,
) -> Tensor:
    q = _linear(x, weights.get(f"{prefix}.self_attn.q_proj.weight"), runtime)
    k = _linear(x, weights.get(f"{prefix}.self_attn.k_proj.weight"), runtime)
    v = _linear(x, weights.get(f"{prefix}.self_attn.v_proj.weight"), runtime)
    qh = _reshape_heads(q, cfg.num_attention_heads, cfg.resolved_head_dim)
    kh = _reshape_heads(k, cfg.num_key_value_heads, cfg.resolved_head_dim)
    vh = _reshape_heads(v, cfg.num_key_value_heads, cfg.resolved_head_dim)
    qh = _apply_head_norm(qh, weights.get(f"{prefix}.self_attn.q_norm.weight"), cfg.rms_norm_eps, runtime)
    kh = _apply_head_norm(kh, weights.get(f"{prefix}.self_attn.k_norm.weight"), cfg.rms_norm_eps, runtime)
    qh = [
        [_rotary(h, position_offset + p, cfg.rope_theta, cfg.rope_scaling_factor, runtime)
         for p, h in enumerate(head)]
        for head in qh
    ]
    kh = [
        [_rotary(h, position_offset + p, cfg.rope_theta, cfg.rope_scaling_factor, runtime)
         for p, h in enumerate(head)]
        for head in kh
    ]

    if cache is not None:
        layer_index = int(prefix.rsplit(".", 1)[-1])
        if not cache.keys[layer_index]:
            cache.keys[layer_index] = [[] for _ in kh]
            cache.values[layer_index] = [[] for _ in vh]
        if len(cache.keys[layer_index]) != len(kh):
            raise ValueError("Qwen3 KV cache head count does not match the model")
        for head in range(len(kh)):
            cache.keys[layer_index][head].extend(kh[head])
            cache.values[layer_index][head].extend(vh[head])
        kh = cache.keys[layer_index]
        vh = cache.values[layer_index]

    kh = _repeat_kv(kh, cfg.kv_group_size)
    vh = _repeat_kv(vh, cfg.kv_group_size)
    attended = _heads_to_tensor(
        _attention(qh, kh, vh, key_position_offset=position_offset, runtime=runtime)
    )
    return _linear(
        attended,
        weights.get(f"{prefix}.self_attn.o_proj.weight"),
        runtime,
    )


def qwen3_mlp(
    x: Tensor,
    weights: ModelWeights,
    prefix: str,
    runtime: TensorRuntime | None = None,
) -> Tensor:
    gate = _linear(x, weights.get(f"{prefix}.mlp.gate_proj.weight"), runtime)
    up = _linear(x, weights.get(f"{prefix}.mlp.up_proj.weight"), runtime)
    silu = (
        runtime.silu(gate)
        if runtime is not None
        else Tensor.from_values(
            gate.shape,
            (g / (1.0 + math.exp(-g)) for g in gate.data),
            dtype=gate.dtype,
        )
    )
    gated = (
        runtime.mul(silu, up)
        if runtime is not None
        else Tensor.from_values(
            gate.shape,
            (s * u for s, u in zip(silu.data, up.data)),
            dtype=gate.dtype,
        )
    )
    return _linear(
        gated,
        weights.get(f"{prefix}.mlp.down_proj.weight"),
        runtime,
    )


class Qwen3Runtime:
    """Native reference runtime for the dense Qwen3 architecture."""

    def __init__(
        self,
        config: Qwen3Config,
        weights: ModelWeights,
        tensor_runtime: TensorRuntime | None = None,
    ) -> None:
        self.config = config
        self.weights = weights
        self.tensor_runtime = tensor_runtime

    def forward(
        self,
        token_ids: Sequence[int],
        cache: Qwen3KVCache | None = None,
    ) -> Tensor:
        if not token_ids:
            raise ValueError("token sequence must not be empty")
        if any(token_id < 0 or token_id >= self.config.vocab_size for token_id in token_ids):
            raise ValueError("token id is outside the Qwen3 vocabulary")
        position_offset = cache.sequence_length if cache is not None else 0
        if position_offset + len(token_ids) > self.config.max_position_embeddings:
            raise ValueError("token sequence exceeds Qwen3 context length")
        if cache is not None and len(cache.keys) != self.config.num_hidden_layers:
            raise ValueError("Qwen3 KV cache layer count does not match the model")

        embedding = self.weights.get("model.embed_tokens.weight")
        hidden = Tensor.from_values(
            (len(token_ids), self.config.hidden_size),
            (
                v
                for token_id in token_ids
                for v in embedding.data[
                    token_id * self.config.hidden_size:
                    (token_id + 1) * self.config.hidden_size
                ]
            ),
        )
        for layer in range(self.config.num_hidden_layers):
            prefix = f"model.layers.{layer}"
            normed = _rms_norm(
                hidden,
                self.weights.get(f"{prefix}.input_layernorm.weight"),
                self.config.rms_norm_eps,
                self.tensor_runtime,
            )
            attention = qwen3_attention(
                normed,
                self.weights,
                prefix,
                self.config,
                cache,
                position_offset,
                self.tensor_runtime,
            )
            hidden = (
                self.tensor_runtime.add(hidden, attention)
                if self.tensor_runtime is not None
                else add(hidden, attention)
            )
            normed = _rms_norm(
                hidden,
                self.weights.get(f"{prefix}.post_attention_layernorm.weight"),
                self.config.rms_norm_eps,
                self.tensor_runtime,
            )
            mlp = qwen3_mlp(
                normed,
                self.weights,
                prefix,
                self.tensor_runtime,
            )
            hidden = (
                self.tensor_runtime.add(hidden, mlp)
                if self.tensor_runtime is not None
                else add(hidden, mlp)
            )
        hidden = _rms_norm(
            hidden,
            self.weights.get("model.norm.weight"),
            self.config.rms_norm_eps,
            self.tensor_runtime,
        )
        lm_head = (
            self.weights.get("lm_head.weight")
            if self.weights.contains("lm_head.weight")
            else embedding
        )
        return _linear(hidden, lm_head, self.tensor_runtime)

    def generate_greedy(
        self,
        token_ids: Sequence[int],
        max_new_tokens: int,
        eos_token_id: int | None = None,
    ) -> list[int]:
        """Generate tokens using native Coreless greedy decoding and KV cache."""
        if max_new_tokens < 0:
            raise ValueError("max_new_tokens must be non-negative")
        generated = list(token_ids)
        if not generated or max_new_tokens == 0:
            return generated
        cache = Qwen3KVCache.create(self.config.num_hidden_layers)
        logits = self.forward(generated, cache)
        for _ in range(max_new_tokens):
            row = logits.data[-self.config.vocab_size:]
            next_token = max(range(len(row)), key=row.__getitem__)
            generated.append(next_token)
            if eos_token_id is not None and next_token == eos_token_id:
                break
            logits = self.forward([next_token], cache)
        return generated
