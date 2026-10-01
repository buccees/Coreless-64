"""Coreless-native tensor execution and persistence boundary.

The runtime keeps tensor semantics independent of host ML frameworks. It can
execute deterministic dense operations and persist tensor values in the
Coreless machine image so model data can survive a power cycle.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from typing import Iterable

from .tensor import Tensor, add, dot, matmul, mul, relu, softmax, sub


@dataclass
class TensorRuntime:
    """Dependency-free tensor runtime bound to a Coreless storage image."""

    storage: object | None = None
    cpu: object | None = None
    namespace: str = "tensor"

    _ELEMENT_TYPES = {"int8": 0, "int16": 1, "int32": 2, "int64": 3,
                      "fp16": 4, "bf16": 5, "fp32": 6, "fp64": 7}
    _MATRIX_SHAPES = ((2, 2, 2), (4, 4, 4), (8, 8, 8),
                      (8, 16, 16), (16, 8, 16), (16, 16, 16))

    def create(self, shape: Iterable[int], values: Iterable[float], dtype: str = "fp64") -> Tensor:
        return Tensor.from_values(tuple(shape), values, dtype=dtype)

    def bind_cpu(self, cpu: object) -> "TensorRuntime":
        """Bind tensor execution to a Coreless architectural vector/matrix unit."""
        if not hasattr(cpu, "vector") or not hasattr(cpu, "matrix"):
            raise TypeError("CPU does not expose Coreless vector/matrix state")
        self.cpu = cpu
        return self

    def add(self, left: Tensor, right: Tensor) -> Tensor:
        return add(left, right)

    def matmul(self, left: Tensor, right: Tensor) -> Tensor:
        return matmul(left, right)

    def sub(self, left: Tensor, right: Tensor) -> Tensor:
        return sub(left, right)

    def mul(self, left: Tensor, right: Tensor) -> Tensor:
        return mul(left, right)

    def dot(self, left: Tensor, right: Tensor) -> float:
        return dot(left, right)

    def relu(self, value: Tensor) -> Tensor:
        return relu(value)

    def softmax(self, value: Tensor) -> Tensor:
        return softmax(value)

    @classmethod
    def _element_type(cls, dtype: str) -> int:
        try:
            return cls._ELEMENT_TYPES[dtype]
        except KeyError as exc:
            raise ValueError("unsupported tensor dtype") from exc

    @staticmethod
    def _encode_value(value: float, dtype: str) -> int:
        if dtype.startswith("int"):
            bits = int(dtype[3:])
            if not float(value).is_integer():
                raise ValueError("integer tensor contains a non-integer value")
            return int(value) & ((1 << bits) - 1)
        if dtype == "fp16":
            return int.from_bytes(struct.pack("<e", float(value)), "little")
        if dtype == "bf16":
            raw = int.from_bytes(struct.pack("<f", float(value)), "little")
            low, high = raw & 0xFFFF, raw >> 16
            if low > 0x8000 or (low == 0x8000 and (high & 1)):
                high = (high + 1) & 0xFFFF
            return high
        if dtype == "fp32":
            return int.from_bytes(struct.pack("<f", float(value)), "little")
        if dtype == "fp64":
            return int.from_bytes(struct.pack("<d", float(value)), "little")
        raise ValueError("unsupported tensor dtype")

    @staticmethod
    def _decode_value(raw: int, dtype: str) -> float:
        if dtype.startswith("int"):
            bits = int(dtype[3:])
            raw &= (1 << bits) - 1
            if raw & (1 << (bits - 1)):
                raw -= 1 << bits
            return float(raw)
        if dtype == "fp16":
            return struct.unpack("<e", (raw & 0xFFFF).to_bytes(2, "little"))[0]
        if dtype == "bf16":
            return struct.unpack("<f", ((raw & 0xFFFF) << 16).to_bytes(4, "little"))[0]
        if dtype == "fp32":
            return struct.unpack("<f", (raw & 0xFFFFFFFF).to_bytes(4, "little"))[0]
        if dtype == "fp64":
            return struct.unpack("<d", (raw & ((1 << 64) - 1)).to_bytes(8, "little"))[0]
        raise ValueError("unsupported tensor dtype")

    def _require_cpu(self):
        if self.cpu is None:
            raise RuntimeError("tensor runtime is not bound to a Coreless CPU")
        return self.cpu

    @staticmethod
    def _same_vector_inputs(left: Tensor, right: Tensor) -> None:
        if left.shape != right.shape or len(left.shape) != 1:
            raise ValueError("native vector execution requires equal rank-1 shapes")
        if left.dtype != right.dtype:
            raise ValueError("native vector execution requires matching dtypes")
        if left.size > 64:
            raise ValueError("native Coreless vector length is 64 lanes")

    def vector_add(self, left: Tensor, right: Tensor) -> Tensor:
        return self._vector_binary(left, right, 0x00)

    def vector_mul(self, left: Tensor, right: Tensor) -> Tensor:
        return self._vector_binary(left, right, 0x02)

    def _vector_binary(self, left: Tensor, right: Tensor, op: int) -> Tensor:
        self._same_vector_inputs(left, right)
        cpu = self._require_cpu()
        et = self._element_type(left.dtype)
        saved = {r: cpu.vector[r][:] for r in (29, 30, 31)}
        old_vl, old_vstart, old_vtype = cpu.vector_vl, cpu.vector_vstart, cpu.vector_vtype
        try:
            cpu.vector[29][:left.size] = [self._encode_value(v, left.dtype) for v in left.data]
            cpu.vector[30][:right.size] = [self._encode_value(v, right.dtype) for v in right.data]
            cpu.vector_vl, cpu.vector_vstart, cpu.vector_vtype = left.size, 0, et
            cpu._vector_op(3, op, 31, 29, 30, et << 29)
            values = [self._decode_value(cpu.vector[31][i], left.dtype) for i in range(left.size)]
            return Tensor.from_values(left.shape, values, dtype=left.dtype)
        finally:
            for r, values in saved.items():
                cpu.vector[r][:] = values
            cpu.vector_vl, cpu.vector_vstart, cpu.vector_vtype = old_vl, old_vstart, old_vtype

    def vector_dot(self, left: Tensor, right: Tensor) -> float:
        self._same_vector_inputs(left, right)
        cpu = self._require_cpu()
        et = self._element_type(left.dtype)
        saved_vector = {r: cpu.vector[r][:] for r in (29, 30, 31)}
        saved_regs = {r: cpu.read_reg(r) for r in (29, 30, 31)}
        old_vl, old_vstart, old_vtype = cpu.vector_vl, cpu.vector_vstart, cpu.vector_vtype
        try:
            cpu.vector[29][:left.size] = [self._encode_value(v, left.dtype) for v in left.data]
            cpu.vector[30][:right.size] = [self._encode_value(v, right.dtype) for v in right.data]
            cpu.vector_vl, cpu.vector_vstart, cpu.vector_vtype = left.size, 0, et
            cpu._vector_op(3, 0x02, 31, 29, 30, et << 29)
            cpu._vector_op(3, 0x18, 31, 31, 30, et << 29)
            raw = cpu.vector[31][0] if left.dtype.startswith("fp") or left.dtype == "bf16" else cpu.read_reg(31)
            return self._decode_value(raw, left.dtype)
        finally:
            for r, values in saved_vector.items():
                cpu.vector[r][:] = values
            for r, value in saved_regs.items():
                cpu.write_reg(r, value)
            cpu.vector_vl, cpu.vector_vstart, cpu.vector_vtype = old_vl, old_vstart, old_vtype

    def matrix_matmul(self, left: Tensor, right: Tensor) -> Tensor:
        if len(left.shape) != 2 or len(right.shape) != 2:
            raise ValueError("native matrix execution requires rank-2 tensors")
        if left.shape[1] != right.shape[0]:
            raise ValueError("matrix dimensions do not agree")
        if left.dtype != right.dtype or not left.dtype.startswith("int"):
            raise ValueError("native Coreless matrix baseline requires matching integer dtypes")
        shape = left.shape[0], right.shape[1], left.shape[1]
        if shape not in self._MATRIX_SHAPES:
            raise ValueError("matrix shape is not supported by the Coreless baseline")
        cpu = self._require_cpu()
        et = self._element_type(left.dtype)
        shape_index = self._MATRIX_SHAPES.index(shape)
        saved = {r: [row[:] for row in cpu.matrix[r]] for r in (29, 30, 31)}
        old_shape = cpu.matrix_shape
        try:
            for i, row in enumerate(left.shape and range(left.shape[0])):
                for j in range(left.shape[1]):
                    cpu.matrix[29][i][j] = self._encode_value(left.at(i, j), left.dtype)
            for i, row in enumerate(range(right.shape[0])):
                for j in range(right.shape[1]):
                    cpu.matrix[30][i][j] = self._encode_value(right.at(i, j), right.dtype)
            cpu.matrix_shape = shape
            cpu._matrix_op(0x00, 31, 29, 30, (et << 29) | (et << 26) | (shape_index << 23) | (1 << 22), 0, 0)
            values = [self._decode_value(cpu.matrix[31][i][j], left.dtype)
                      for i in range(shape[0]) for j in range(shape[1])]
            return Tensor.from_values((shape[0], shape[1]), values, dtype=left.dtype)
        finally:
            for r, rows in saved.items():
                cpu.matrix[r][:] = rows
            cpu.matrix_shape = old_shape

    def save(self, name: str, value: Tensor) -> str:
        if self.storage is None:
            raise RuntimeError("tensor runtime has no persistent storage")
        if not name or "/" in name:
            raise ValueError("tensor name must be a non-empty local name")
        key = f"{self.namespace}/{name}"
        payload = json.dumps(
            {"version": 2, "shape": list(value.shape), "dtype": value.dtype, "data": list(value.data)},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self.storage.put(key, payload, sync=False)
        return key

    def load(self, name: str) -> Tensor:
        if self.storage is None:
            raise RuntimeError("tensor runtime has no persistent storage")
        key = f"{self.namespace}/{name}"
        raw = self.storage.objects.get(key)
        if raw is None:
            raise KeyError(name)
        payload = json.loads(raw.decode("utf-8"))
        if payload.get("version") not in (1, 2):
            raise ValueError("unsupported tensor format version")
        return Tensor.from_values(payload["shape"], payload["data"], dtype=payload.get("dtype", "fp64"))
