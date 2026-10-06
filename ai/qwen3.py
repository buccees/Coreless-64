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

    keys: list[Tensor | None]
    values: list[Tensor | None]

    @classmethod
    def create(cls, num_layers: int) -> "Qwen3KVCache":
        return cls([None for _ in range(num_layers)], [None for _ in range(num_layers)])

    @property
    def sequence_length(self) -> int:
        if not self.keys or self.keys[0] is None:
            return 0
        return self.keys[0].shape[1]

    def append(
        self,
        layer_index: int,
        key: Tensor,
        value: Tensor,
        runtime: TensorRuntime | None = None,
    ) -> tuple[Tensor, Tensor]:
        """Update one layer's cache through the Coreless tensor boundary."""
        if layer_index < 0 or layer_index >= len(self.keys):
            raise IndexError("Qwen3 KV cache layer index out of range")
        if key.shape != value.shape or len(key.shape) != 3:
            raise ValueError("Qwen3 KV cache key/value tensors must have matching rank-3 shapes")
        if key.dtype != value.dtype:
            raise ValueError("Qwen3 KV cache key/value dtypes must match")
        old_key = self.keys[layer_index]
        old_value = self.values[layer_index]
        if old_key is None or old_value is None:
            self.keys[layer_index] = key
            self.values[layer_index] = value
        elif runtime is not None:
            self.keys[layer_index] = runtime.append_sequence(old_key, key)
            self.values[layer_index] = runtime.append_sequence(old_value, value)
        else:
            self.keys[layer_index] = Tensor.from_values(
                (old_key.shape[0], old_key.shape[1] + key.shape[1], old_key.shape[2]),
                old_key.data + key.data,
                dtype=old_key.dtype,
            )
            self.values[layer_index] = Tensor.from_values(
                (old_value.shape[0], old_value.shape[1] + value.shape[1], old_value.shape[2]),
                old_value.data + value.data,
                dtype=old_value.dtype,
            )
        return self.keys[layer_index], self.values[layer_index]


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


def _transpose(x: Tensor, runtime: TensorRuntime | None = None) -> Tensor:
    if runtime is not None:
        return runtime.transpose(x)
    rows, cols = x.shape
    return Tensor.from_values(
        (cols, rows),
        (x.at(r, c) for c in range(cols) for r in range(rows)),
        dtype=x.dtype,
    )


def _reshape_heads(x: Tensor, heads: int, head_dim: int, runtime: TensorRuntime | None = None) -> Tensor:
    if runtime is not None:
        return runtime.reshape_heads(x, heads, head_dim)
    if x.shape[1] != heads * head_dim:
        raise ValueError("projection shape does not match Qwen3 head dimensions")
    return Tensor.from_values(
        (heads, x.shape[0], head_dim),
        (x.data[(pos * heads + head) * head_dim + dim]
         for head in range(heads) for pos in range(x.shape[0]) for dim in range(head_dim)),
        dtype=x.dtype,
    )


def _tensor_heads_to_lists(value: Tensor) -> list[list[list[float]]]:
    if len(value.shape) != 3:
        raise ValueError("head tensor must be rank-3")
    heads, positions, dim = value.shape
    return [[[value.at(head, pos, d) for d in range(dim)] for pos in range(positions)] for head in range(heads)]


def _heads_tensor_from_lists(heads: list[list[list[float]]], dtype: str = "fp64") -> Tensor:
    if not heads:
        raise ValueError("head tensor requires at least one head")
    positions = len(heads[0])
    dim = len(heads[0][0])
    return Tensor.from_values(
        (len(heads), positions, dim),
        (v for head in heads for pos in head for v in pos),
        dtype=dtype,
    )


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
    angles = runtime.rope_angles(
        half, position, theta, scaling_factor=scaling_factor, dtype="fp64"
    )
    c = runtime.cos(angles)
    s = runtime.sin(angles)
    ac = runtime.mul(a, c)
    bs = runtime.mul(b, s)
    as_ = runtime.mul(a, s)
    bc = runtime.mul(b, c)
    first = runtime.sub(ac, bs)
    second = runtime.add(as_, bc)
    return list(first.data) + list(second.data)


def _repeat_kv(heads: Tensor, repeats: int, runtime: TensorRuntime | None = None) -> Tensor:
    if runtime is not None:
        return runtime.repeat_heads(heads, repeats)
    if len(heads.shape) != 3:
        raise ValueError("KV heads must be rank-3")
    h, positions, dim = heads.shape
    return Tensor.from_values(
        (h * repeats, positions, dim),
        (heads.at(head, pos, d) for head in range(h) for _ in range(repeats)
         for pos in range(positions) for d in range(dim)),
        dtype=heads.dtype,
    )


def _attention(
    q,
    k,
    v,
    causal=True,
    key_position_offset=0,
    runtime: TensorRuntime | None = None,
) -> list[list[float]]:
    """Execute attention score/value products through the Coreless tensor boundary."""
    if runtime is None:
        raise ValueError("tensor-native attention requires TensorRuntime")
    q_tensor = Tensor.from_values(
        (len(q), len(q[0]), len(q[0][0])),
        (value for head in q for row in head for value in row),
    )
    k_tensor = Tensor.from_values(
        (len(k), len(k[0]), len(k[0][0])),
        (value for head in k for row in head for value in row),
    )
    v_tensor = Tensor.from_values(
        (len(v), len(v[0]), len(v[0][0])),
        (value for head in v for row in head for value in row),
    )
    reduced = _attention_tensor(
        q_tensor, k_tensor, v_tensor,
        causal=causal,
        key_position_offset=key_position_offset,
        runtime=runtime,
    )
    return [
        [reduced.at(row, dim_index) for dim_index in range(reduced.shape[1])]
        for row in range(reduced.shape[0])
    ]

def _attention_tensor(
    q: Tensor,
    k: Tensor,
    v: Tensor,
    causal: bool = True,
    key_position_offset: int = 0,
    runtime: TensorRuntime | None = None,
) -> Tensor:
    """Keep the complete attention computation inside TensorRuntime."""
    if runtime is None:
        raise ValueError("tensor-native attention requires TensorRuntime")
    return runtime.attention(
        q,
        k,
        v,
        causal=causal,
        key_position_offset=key_position_offset,
    )

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
    if runtime is not None:
        return runtime.rms_norm_rows(x, weight, eps=eps)
    hidden = x.shape[1]
    rows = []
    for row in range(x.shape[0]):
        chunk = Tensor.from_values(
            (hidden,),
            x.data[row * hidden:(row + 1) * hidden],
            dtype=x.dtype,
        )
        squared = sum(v * v for v in chunk.data) / hidden
        scale = (squared + eps) ** -0.5
        weighted = Tensor.from_values(
            (hidden,),
            (v * scale * w for v, w in zip(chunk.data, weight.data)),
            dtype=x.dtype,
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
    return multiply(x, _transpose(weight, runtime))


def _head_rms_norm(
    value: Tensor,
    weight: Tensor,
    eps: float,
    runtime: TensorRuntime | None = None,
) -> Tensor:
    """Apply RMSNorm independently to every vector in a head tensor."""
    if runtime is None:
        return value
    return runtime.rms_norm_heads(value, weight, eps=eps)


def _rotary_tensor(
    value: Tensor,
    position_offset: int,
    theta: float,
    scaling_factor: float | None,
    runtime: TensorRuntime | None = None,
) -> Tensor:
    """Apply rotary embeddings through one native TensorRuntime operation."""
    if runtime is None:
        return value
    return runtime.rotary_embedding(
        value,
        position_offset=position_offset,
        theta=theta,
        scaling_factor=scaling_factor,
    )

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
    qh = _reshape_heads(q, cfg.num_attention_heads, cfg.resolved_head_dim, runtime)
    kh = _reshape_heads(k, cfg.num_key_value_heads, cfg.resolved_head_dim, runtime)
    vh = _reshape_heads(v, cfg.num_key_value_heads, cfg.resolved_head_dim, runtime)
    qh = _head_rms_norm(
        qh,
        weights.get(f"{prefix}.self_attn.q_norm.weight"),
        cfg.rms_norm_eps,
        runtime,
    )
    kh = _head_rms_norm(
        kh,
        weights.get(f"{prefix}.self_attn.k_norm.weight"),
        cfg.rms_norm_eps,
        runtime,
    )
    qh = _rotary_tensor(
        qh, position_offset, cfg.rope_theta, cfg.rope_scaling_factor, runtime
    )
    kh = _rotary_tensor(
        kh, position_offset, cfg.rope_theta, cfg.rope_scaling_factor, runtime
    )

    if cache is not None:
        layer_index = int(prefix.rsplit(".", 1)[-1])
        if cache.keys[layer_index] is None:
            cache.keys[layer_index] = kh
            cache.values[layer_index] = vh
        else:
            old_k = cache.keys[layer_index]
            old_v = cache.values[layer_index]
            if runtime is not None:
                cache.keys[layer_index] = runtime.append_sequence(old_k, kh)
                cache.values[layer_index] = runtime.append_sequence(old_v, vh)
            else:
                cache.keys[layer_index] = Tensor.from_values(
                    (old_k.shape[0], old_k.shape[1] + kh.shape[1], old_k.shape[2]),
                    old_k.data + kh.data,
                    dtype=old_k.dtype,
                )
                cache.values[layer_index] = Tensor.from_values(
                    (old_v.shape[0], old_v.shape[1] + vh.shape[1], old_v.shape[2]),
                    old_v.data + vh.data,
                    dtype=old_v.dtype,
                )
        kh = cache.keys[layer_index]
        vh = cache.values[layer_index]

    kh = _repeat_kv(kh, cfg.kv_group_size, runtime)
    vh = _repeat_kv(vh, cfg.kv_group_size, runtime)
    attended = _attention_tensor(
        qh,
        kh,
        vh,
        key_position_offset=position_offset,
        runtime=runtime,
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
        if self.tensor_runtime is not None:
            hidden = self.tensor_runtime.embedding_lookup(embedding, token_ids)
        else:
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
                dtype=embedding.dtype,
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
            if self.tensor_runtime is not None:
                row = self.tensor_runtime.last_row(logits)
            else:
                row = Tensor.from_values(
                    (1, self.config.vocab_size),
                    logits.data[-self.config.vocab_size:],
                    dtype=logits.dtype,
                )
            next_token = (
                self.tensor_runtime.argmax(row)
                if self.tensor_runtime is not None
                else max(range(len(row.data)), key=row.data.__getitem__)
            )
            generated.append(next_token)
            if eos_token_id is not None and next_token == eos_token_id:
                break
            logits = self.forward([next_token], cache)
        return generated
