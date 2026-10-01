"""Qwen3-native model configuration and artifact validation.

This module validates the native Qwen3 tensor contract from safetensors
metadata before expensive weight materialization.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model_loader import _index_files
from .qwen3 import Qwen3Config


def load_qwen3_config(path: str | Path) -> Qwen3Config:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Qwen3 config must be a JSON object")
    if data.get("model_type") not in (None, "qwen3"):
        raise ValueError("config is not a Qwen3 model")
    rope_scaling = data.get("rope_scaling")
    factor = None
    original_max = None
    if isinstance(rope_scaling, dict):
        raw_factor = rope_scaling.get("factor")
        if raw_factor is not None:
            factor = float(raw_factor)
        raw_original = rope_scaling.get("original_max_position_embeddings")
        if raw_original is not None:
            original_max = int(raw_original)
    return Qwen3Config(
        hidden_size=int(data["hidden_size"]),
        intermediate_size=int(data["intermediate_size"]),
        num_hidden_layers=int(data["num_hidden_layers"]),
        num_attention_heads=int(data["num_attention_heads"]),
        num_key_value_heads=int(data["num_key_value_heads"]),
        vocab_size=int(data["vocab_size"]),
        max_position_embeddings=int(data["max_position_embeddings"]),
        rms_norm_eps=float(data.get("rms_norm_eps", 1e-6)),
        head_dim=int(data["head_dim"]) if data.get("head_dim") is not None else None,
        rope_theta=float(data.get("rope_theta", 1000000.0)),
        rope_scaling_factor=factor,
        original_max_position_embeddings=original_max,
    )


def _headers(directory: Path) -> dict[str, tuple[str, tuple[int, ...]]]:
    headers: dict[str, tuple[str, tuple[int, ...]]] = {}
    import struct
    for shard in _index_files(directory):
        blob = shard.read_bytes()
        if len(blob) < 8:
            raise ValueError(f"truncated safetensors file: {shard.name}")
        header_len = struct.unpack_from("<Q", blob, 0)[0]
        end = 8 + header_len
        if end > len(blob):
            raise ValueError(f"invalid safetensors header: {shard.name}")
        data = json.loads(blob[8:end].decode("utf-8"))
        for name, entry in data.items():
            if name == "__metadata__":
                continue
            if name in headers:
                raise ValueError(f"duplicate tensor across shards: {name}")
            headers[name] = (str(entry["dtype"]), tuple(int(v) for v in entry["shape"]))
    return headers


def validate_qwen3_artifact(directory: str | Path) -> tuple[str, ...]:
    root = Path(directory)
    cfg = load_qwen3_config(root / "config.json")
    headers = _headers(root)

    required = {"model.embed_tokens.weight", "model.norm.weight"}
    expected = {
        "model.embed_tokens.weight": (cfg.vocab_size, cfg.hidden_size),
        "model.norm.weight": (cfg.hidden_size,),
    }
    tie_word_embeddings = bool(
        json.loads((root / "config.json").read_text(encoding="utf-8"))
        .get("tie_word_embeddings", False)
    )
    if not tie_word_embeddings:
        required.add("lm_head.weight")
        expected["lm_head.weight"] = (cfg.vocab_size, cfg.hidden_size)
    for layer in range(cfg.num_hidden_layers):
        p = f"model.layers.{layer}"
        layer_expected = {
            f"{p}.input_layernorm.weight": (cfg.hidden_size,),
            f"{p}.self_attn.q_proj.weight": (cfg.num_attention_heads * cfg.resolved_head_dim, cfg.hidden_size),
            f"{p}.self_attn.k_proj.weight": (cfg.num_key_value_heads * cfg.resolved_head_dim, cfg.hidden_size),
            f"{p}.self_attn.v_proj.weight": (cfg.num_key_value_heads * cfg.resolved_head_dim, cfg.hidden_size),
            f"{p}.self_attn.q_norm.weight": (cfg.resolved_head_dim,),
            f"{p}.self_attn.k_norm.weight": (cfg.resolved_head_dim,),
            f"{p}.self_attn.o_proj.weight": (cfg.hidden_size, cfg.num_attention_heads * cfg.resolved_head_dim),
            f"{p}.post_attention_layernorm.weight": (cfg.hidden_size,),
            f"{p}.mlp.gate_proj.weight": (cfg.intermediate_size, cfg.hidden_size),
            f"{p}.mlp.up_proj.weight": (cfg.intermediate_size, cfg.hidden_size),
            f"{p}.mlp.down_proj.weight": (cfg.hidden_size, cfg.intermediate_size),
        }
        expected.update(layer_expected)
        required.update(layer_expected)
    missing = sorted(required - headers.keys())
    if missing:
        raise ValueError(f"Qwen3 artifact is missing tensors: {missing[:8]}")
    for name, shape in expected.items():
        actual = headers[name][1]
        if actual != shape:
            raise ValueError(f"Qwen3 tensor shape mismatch for {name}: {actual} != {shape}")
    return tuple(sorted(headers))
