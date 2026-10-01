from pathlib import Path
import json
import struct

from qwen3_model import load_qwen3_model


def _write(path: Path, entries):
    payload = b""
    offsets = {}
    for name, (dtype, shape) in entries.items():
        count = 1
        for n in shape:
            count *= n
        raw = b"\x00" * (count * 4)
        start = len(payload)
        payload += raw
        offsets[name] = {
            "dtype": dtype, "shape": list(shape),
            "data_offsets": [start, len(payload)],
        }
    header = json.dumps({**offsets, "__metadata__": {}}).encode()
    path.write_bytes(struct.pack("<Q", len(header)) + header + payload)


def test_qwen3_model_uses_storage_backed_weights(tmp_path):
    config = {
        "model_type": "qwen3", "hidden_size": 4, "intermediate_size": 8,
        "num_hidden_layers": 1, "num_attention_heads": 2,
        "num_key_value_heads": 1, "head_dim": 2, "vocab_size": 4,
        "max_position_embeddings": 8, "rms_norm_eps": 1e-6,
        "rope_theta": 1000000.0,
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    names = {
        "model.embed_tokens.weight": ("F32", (4, 4)),
        "model.norm.weight": ("F32", (4,)),
        "lm_head.weight": ("F32", (4, 4)),
        "model.layers.0.input_layernorm.weight": ("F32", (4,)),
        "model.layers.0.self_attn.q_proj.weight": ("F32", (4, 4)),
        "model.layers.0.self_attn.k_proj.weight": ("F32", (2, 4)),
        "model.layers.0.self_attn.v_proj.weight": ("F32", (2, 4)),
        "model.layers.0.self_attn.q_norm.weight": ("F32", (2,)),
        "model.layers.0.self_attn.k_norm.weight": ("F32", (2,)),
        "model.layers.0.self_attn.o_proj.weight": ("F32", (4, 4)),
        "model.layers.0.post_attention_layernorm.weight": ("F32", (4,)),
        "model.layers.0.mlp.gate_proj.weight": ("F32", (8, 4)),
        "model.layers.0.mlp.up_proj.weight": ("F32", (8, 4)),
        "model.layers.0.mlp.down_proj.weight": ("F32", (4, 8)),
    }
    _write(tmp_path / "model.safetensors", names)
    runtime = load_qwen3_model(tmp_path)
    assert runtime.forward([1]).shape == (1, 4)
