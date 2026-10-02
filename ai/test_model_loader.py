import json
import struct

from ai.model_architecture import TransformerConfig
from ai.model_loader import load_config, load_safetensors, load_transformer_model
from ai.tensor import Tensor


def _write_safetensors(path, entries):
    payload = bytearray()
    header = {}
    for name, dtype, shape, raw in entries:
        start = len(payload)
        payload.extend(raw)
        header[name] = {
            "dtype": dtype,
            "shape": list(shape),
            "data_offsets": [start, len(payload)],
        }
    header_bytes = json.dumps(header, separators=(",", ":")).encode()
    path.write_bytes(struct.pack("<Q", len(header_bytes)) + header_bytes + payload)


def test_load_config_aliases(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "d_model": 8,
        "n_inner": 16,
        "n_layer": 2,
        "n_head": 2,
        "vocab_size": 32,
        "n_positions": 128,
    }))
    config = load_config(path)
    assert config == TransformerConfig(8, 16, 2, 2, 32, 128)


def test_load_safetensors_float32(tmp_path):
    path = tmp_path / "model.safetensors"
    raw = struct.pack("<3f", 1.5, -2.0, 4.25)
    _write_safetensors(path, [("embedding", "F32", (3,), raw)])
    weights = load_safetensors(path)
    assert weights.get("embedding") == Tensor.from_values((3,), [1.5, -2.0, 4.25], dtype="fp32")


def test_load_safetensors_bfloat16(tmp_path):
    path = tmp_path / "model.safetensors"
    raw = b"".join(struct.pack("<H", bits >> 16) for bits in (
        struct.unpack("<I", struct.pack("<f", 1.5))[0],
        struct.unpack("<I", struct.pack("<f", -2.0))[0],
    ))
    _write_safetensors(path, [("x", "BF16", (2,), raw)])
    tensor = load_safetensors(path).get("x")
    assert tensor.dtype == "bf16"
    values = tensor.data
    assert abs(values[0] - 1.5) < 0.001
    assert abs(values[1] + 2.0) < 0.001


def test_load_sharded_model(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({
        "hidden_size": 2,
        "intermediate_size": 4,
        "num_layers": 1,
        "num_attention_heads": 1,
        "vocab_size": 3,
        "max_position_embeddings": 8,
    }))
    raw_a = struct.pack("<2f", 1.0, 2.0)
    raw_b = struct.pack("<2f", 3.0, 4.0)
    _write_safetensors(tmp_path / "a.safetensors", [("a", "F32", (2,), raw_a)])
    _write_safetensors(tmp_path / "b.safetensors", [("b", "F32", (2,), raw_b)])
    (tmp_path / "model.safetensors.index.json").write_text(json.dumps({
        "weight_map": {"a": "a.safetensors", "b": "b.safetensors"}
    }))
    config, weights = load_transformer_model(tmp_path)
    assert config.hidden_size == 2
    assert weights.names() == ("a", "b")
