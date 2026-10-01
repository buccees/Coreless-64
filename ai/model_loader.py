"""Dependency-free model artifact loading for Coreless.

The loader translates common Hugging Face-style model directories into the
Coreless-native TransformerConfig and ModelWeights contracts. It supports
config.json plus safetensors files (including sharded safetensors indexes).

No external ML framework is required. Model files remain external runtime
assets and are never committed to this repository.
"""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path
from typing import Any, Iterable

from .model_architecture import TransformerConfig, from_mapping
from .model_weights import ModelTensor, ModelWeights
from .tensor import Tensor


_DTYPE_FORMAT = {
    "F16": ("<e", 2),
    "F32": ("<f", 4),
    "F64": ("<d", 8),
}


def load_config(path: str | Path) -> TransformerConfig:
    """Load a common model config JSON into Coreless TransformerConfig."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("model config must be a JSON object")
    return from_mapping(data)


def _bfloat16_to_float(raw: bytes) -> float:
    bits = int.from_bytes(raw, "little") << 16
    return struct.unpack("<f", bits.to_bytes(4, "little"))[0]


def _decode_tensor(raw: bytes, dtype: str, shape: tuple[int, ...]) -> Tensor:
    if dtype == "BF16":
        if len(raw) % 2:
            raise ValueError("invalid BF16 tensor byte length")
        values = (_bfloat16_to_float(raw[i:i + 2]) for i in range(0, len(raw), 2))
    elif dtype in _DTYPE_FORMAT:
        fmt, width = _DTYPE_FORMAT[dtype]
        if len(raw) % width:
            raise ValueError(f"invalid {dtype} tensor byte length")
        count = len(raw) // width
        values = (struct.unpack_from(fmt, raw, i * width)[0] for i in range(count))
    else:
        raise ValueError(f"unsupported safetensors dtype: {dtype}")

    values = tuple(float(v) for v in values)
    expected = math.prod(shape)
    if len(values) != expected:
        raise ValueError("tensor byte count does not match tensor shape")
    return Tensor.from_values(shape, values)


def load_safetensors(path: str | Path) -> ModelWeights:
    """Load one safetensors file into Coreless ModelWeights.

    The safetensors header and tensor payload are validated before conversion.
    Metadata entries are ignored; only named tensor entries are imported.
    """
    blob = Path(path).read_bytes()
    if len(blob) < 8:
        raise ValueError("safetensors file is truncated")
    header_len = struct.unpack_from("<Q", blob, 0)[0]
    header_start = 8
    header_end = header_start + header_len
    if header_end > len(blob):
        raise ValueError("safetensors header exceeds file size")

    header = json.loads(blob[header_start:header_end].decode("utf-8"))
    if not isinstance(header, dict):
        raise ValueError("safetensors header must be an object")

    tensors: list[ModelTensor] = []
    for name, entry in header.items():
        if name == "__metadata__":
            continue
        if not isinstance(entry, dict):
            raise ValueError(f"invalid tensor entry: {name}")
        dtype = entry.get("dtype")
        shape = tuple(int(v) for v in entry.get("shape", ()))
        offsets = entry.get("data_offsets")
        if not isinstance(dtype, str) or not shape or not isinstance(offsets, list) or len(offsets) != 2:
            raise ValueError(f"invalid tensor metadata: {name}")
        start, end = (int(offsets[0]), int(offsets[1]))
        payload_start = header_end + start
        payload_end = header_end + end
        if start < 0 or end < start or payload_end > len(blob):
            raise ValueError(f"invalid tensor offsets: {name}")
        tensors.append(ModelTensor(name, _decode_tensor(
            blob[payload_start:payload_end], dtype, shape
        )))
    return ModelWeights(tensors)


def _index_files(directory: Path) -> tuple[Path, ...]:
    index = directory / "model.safetensors.index.json"
    if index.exists():
        data = json.loads(index.read_text(encoding="utf-8"))
        mapping = data.get("weight_map")
        if not isinstance(mapping, dict):
            raise ValueError("invalid safetensors index: weight_map missing")
        names = tuple(dict.fromkeys(str(v) for v in mapping.values()))
        return tuple(directory / name for name in names)

    single = directory / "model.safetensors"
    if single.exists():
        return (single,)

    candidates = tuple(sorted(directory.glob("*.safetensors")))
    if candidates:
        return candidates
    raise FileNotFoundError("no safetensors model weights found")


def load_model_weights(directory: str | Path) -> ModelWeights:
    """Load all safetensors shards in a model directory."""
    root = Path(directory)
    tensors: list[ModelTensor] = []
    seen: set[str] = set()
    for shard in _index_files(root):
        loaded = load_safetensors(shard)
        for name in loaded.names():
            if name in seen:
                raise ValueError(f"duplicate tensor across shards: {name}")
            seen.add(name)
            tensors.append(ModelTensor(name, loaded.get(name)))
    return ModelWeights(tensors)


def load_transformer_model(directory: str | Path) -> tuple[TransformerConfig, ModelWeights]:
    """Load config.json and all safetensors weights from a model directory."""
    root = Path(directory)
    return load_config(root / "config.json"), load_model_weights(root)
