import json
import struct

from model_loader import load_safetensors_mmap


def _write_safetensors(path):
    payload = struct.pack("<4f", 1.0, 2.0, 3.0, 4.0)
    header = json.dumps({
        "weight": {
            "dtype": "F32",
            "shape": [2, 2],
            "data_offsets": [0, len(payload)],
        }
    }, separators=(",", ":")).encode("utf-8")
    path.write_bytes(struct.pack("<Q", len(header)) + header + payload)


def test_safetensors_mmap_reads_values_without_materializing_tuple(tmp_path):
    path = tmp_path / "model.safetensors"
    _write_safetensors(path)

    weights = load_safetensors_mmap(path)
    tensor = weights.get("weight")

    assert tensor.shape == (2, 2)
    assert tensor.at(0, 0) == 1.0
    assert tensor.at(1, 1) == 4.0
    assert type(tensor.data).__name__ == "_MappedFloatSequence"
