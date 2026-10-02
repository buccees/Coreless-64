from pathlib import Path
import json
import struct

from qwen3_model import load_qwen3_model
from tensor import add, matmul
from tensor_runtime import TensorRuntime


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


def _config(tmp_path):
    config = {
        "model_type": "qwen3", "hidden_size": 4, "intermediate_size": 8,
        "num_hidden_layers": 1, "num_attention_heads": 2,
        "num_key_value_heads": 1, "head_dim": 2, "vocab_size": 4,
        "max_position_embeddings": 8, "rms_norm_eps": 1e-6,
        "rope_theta": 1000000.0,
    }
    (tmp_path / "config.json").write_text(json.dumps(config))


def _names(tied=False):
    names = {
        "model.embed_tokens.weight": ("F32", (4, 4)),
        "model.norm.weight": ("F32", (4,)),
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
    if not tied:
        names["lm_head.weight"] = ("F32", (4, 4))
    return names


def test_qwen3_model_uses_storage_backed_weights(tmp_path):
    _config(tmp_path)
    _write(tmp_path / "model.safetensors", {
        **_names(),
    })
    runtime = load_qwen3_model(tmp_path)
    assert runtime.forward([1]).shape == (1, 4)


def test_qwen3_model_supports_tied_word_embeddings(tmp_path):
    _config(tmp_path)
    config = json.loads((tmp_path / "config.json").read_text())
    config["tie_word_embeddings"] = True
    (tmp_path / "config.json").write_text(json.dumps(config))
    _write(tmp_path / "model.safetensors", _names(tied=True))
    runtime = load_qwen3_model(tmp_path)
    assert runtime.forward([1]).shape == (1, 4)


class TrackingTensorRuntime(TensorRuntime):
    def __init__(self):
        super().__init__()
        self.matmul_calls = 0
        self.add_calls = 0

    def matmul(self, left, right):
        self.matmul_calls += 1
        return matmul(left, right)

    def add(self, left, right):
        self.add_calls += 1
        return add(left, right)


def test_qwen3_model_routes_dense_execution_through_tensor_runtime(tmp_path):
    _config(tmp_path)
    _write(tmp_path / "model.safetensors", _names())
    tensor_runtime = TrackingTensorRuntime()
    runtime = load_qwen3_model(tmp_path, tensor_runtime=tensor_runtime)

    result = runtime.forward([1])

    assert result.shape == (1, 4)
    assert runtime.tensor_runtime is tensor_runtime
    assert tensor_runtime.matmul_calls >= 7
    assert tensor_runtime.add_calls == 2


def test_qwen3_greedy_generation_uses_kv_cache(tmp_path):
    _config(tmp_path)
    _write(tmp_path / "model.safetensors", _names())
    runtime = load_qwen3_model(tmp_path)

    generated = runtime.generate_greedy([1], max_new_tokens=2)

    assert generated == [1, 0, 0]
