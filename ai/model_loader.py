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
    tensor_dtype = {"F16": "fp16", "BF16": "bf16", "F32": "fp32", "F64": "fp64"}.get(dtype)
    if tensor_dtype is None:
        raise ValueError(f"unsupported safetensors dtype: {dtype}")
    return Tensor.from_values(shape, values, dtype=tensor_dtype)


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


class _MappedFloatSequence:
    """Read-only float view over a safetensors payload without materializing it."""

    def __init__(self, handle, offset: int, count: int, dtype: str) -> None:
        self._handle = handle
        self._offset = offset
        self._count = count
        self._dtype = dtype
        if dtype == "BF16":
            self._width = 2
        elif dtype in _DTYPE_FORMAT:
            self._width = _DTYPE_FORMAT[dtype][1]
        else:
            raise ValueError(f"unsupported safetensors dtype: {dtype}")

    def __len__(self) -> int:
        return self._count

    def __getitem__(self, index):
        if isinstance(index, slice):
            return tuple(self[i] for i in range(*index.indices(self._count)))
        if index < 0:
            index += self._count
        if not 0 <= index < self._count:
            raise IndexError("tensor index out of range")
        self._handle.seek(self._offset + index * self._width)
        raw = self._handle.read(self._width)
        if self._dtype == "BF16":
            return _bfloat16_to_float(raw)
        fmt, _ = _DTYPE_FORMAT[self._dtype]
        return struct.unpack(fmt, raw)[0]


def load_safetensors_mmap(path: str | Path) -> ModelWeights:
    """Load a safetensors file with storage-backed tensor values.

    Tensor values are decoded on demand from the model file rather than
    materialized into a Python tuple. The returned ModelWeights retains the
    backing file handles for the lifetime of the weights.
    """
    import mmap

    file_handle = open(path, "rb")
    mapped = mmap.mmap(file_handle.fileno(), 0, access=mmap.ACCESS_READ)
    if len(mapped) < 8:
        mapped.close()
        file_handle.close()
        raise ValueError("safetensors file is truncated")
    header_len = struct.unpack_from("<Q", mapped, 0)[0]
    header_start = 8
    header_end = header_start + header_len
    if header_end > len(mapped):
        mapped.close()
        file_handle.close()
        raise ValueError("safetensors header exceeds file size")

    header = json.loads(mapped[header_start:header_end].decode("utf-8"))
    if not isinstance(header, dict):
        mapped.close()
        file_handle.close()
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
        if start < 0 or end < start or payload_end > len(mapped):
            raise ValueError(f"invalid tensor offsets: {name}")
        count = math.prod(shape)
        if end - start != count * (2 if dtype == "BF16" else _DTYPE_FORMAT.get(dtype, (None, 0))[1]):
            mapped.close()
            file_handle.close()
            raise ValueError(f"tensor byte count does not match tensor shape: {name}")
        tensor_dtype = {"F16": "fp16", "BF16": "bf16", "F32": "fp32", "F64": "fp64"}.get(dtype)
        if tensor_dtype is None:
            mapped.close()
            file_handle.close()
            raise ValueError(f"unsupported safetensors dtype: {dtype}")
        tensor = Tensor(shape, _MappedFloatSequence(
            mapped, payload_start, count, dtype
        ), tensor_dtype)
        tensors.append(ModelTensor(name, tensor))

    loaded = ModelWeights(tensors)
    loaded._backing_handles = (file_handle, mapped)
    return loaded


def load_model_weights_mmap(directory: str | Path) -> ModelWeights:
    """Load all safetensors shards as storage-backed tensors."""
    root = Path(directory)
    tensors: list[ModelTensor] = []
    seen: set[str] = set()
    handles = []
    for shard in _index_files(root):
        loaded = load_safetensors_mmap(shard)
        handles.extend(getattr(loaded, "_backing_handles", ()))
        for name in loaded.names():
            if name in seen:
                raise ValueError(f"duplicate tensor across shards: {name}")
            seen.add(name)
            tensors.append(ModelTensor(name, loaded.get(name)))
    result = ModelWeights(tensors)
    result._backing_handles = tuple(handles)
    return result


def load_transformer_model_mmap(directory: str | Path) -> tuple[TransformerConfig, ModelWeights]:
    """Load config plus storage-backed safetensors weights."""
    root = Path(directory)
    return load_config(root / "config.json"), load_model_weights_mmap(root)
