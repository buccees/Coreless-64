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


def test_qwen3_model_executes_dense_ops_through_coreless_cpu(tmp_path):
    from core import CorelessCPU

    _config(tmp_path)
    _write(tmp_path / "model.safetensors", _names())
    tensor_runtime = TensorRuntime(cpu=CorelessCPU())
    runtime = load_qwen3_model(tmp_path, tensor_runtime=tensor_runtime)

    result = runtime.forward([1])

    assert result.shape == (1, 4)
    assert result.dtype == "fp32"


def test_qwen3_greedy_generation_uses_kv_cache(tmp_path):
    _config(tmp_path)
    _write(tmp_path / "model.safetensors", _names())
    runtime = load_qwen3_model(tmp_path)

    generated = runtime.generate_greedy([1], max_new_tokens=2)

    assert generated == [1, 0, 0]


def test_qwen3_real_forward_preserves_native_runtime_binding(monkeypatch, tmp_path):
    import qwen3_real_artifact as real_artifact

    class FakeTokenizer:
        def encode(self, text):
            return [1]

    class FakeLogits:
        shape = (1, 4)
        data = (0.1, 0.2, 0.9, 0.3)

    class FakeRuntime:
        config = type("Config", (), {"vocab_size": 4})()

        def __init__(self):
            self.tensor_runtime = object()

        def forward(self, token_ids):
            return FakeLogits()

    sentinel = object()
    runtime = FakeRuntime()
    captured = {}

    def fake_load(directory, tensor_runtime=None):
        captured["tensor_runtime"] = tensor_runtime
        return tmp_path, runtime, FakeTokenizer()

    monkeypatch.setattr(real_artifact, "_load_real_artifact", fake_load)

    result = real_artifact.forward_real_artifact(tmp_path, "Hello", sentinel)

    assert captured["tensor_runtime"] is sentinel

    assert result["model"] == "Qwen3-0.6B"
    assert result["input_tokens"] == 1
    assert result["logit_shape"] == (1, 4)
    assert result["next_token_id"] == 2
