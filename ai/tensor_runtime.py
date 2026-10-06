"""Coreless-native tensor execution and persistence boundary.

The runtime keeps tensor semantics independent of host ML frameworks. It can
execute deterministic dense operations and persist tensor values in the
Coreless machine image so model data can survive a power cycle.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from math import exp, fsum
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
    _MATRIX_TILE = 16

    def create(self, shape: Iterable[int], values: Iterable[float], dtype: str = "fp64") -> Tensor:
        return Tensor.from_values(tuple(shape), values, dtype=dtype)

    def bind_cpu(self, cpu: object) -> "TensorRuntime":
        """Bind tensor execution to a Coreless architectural vector/matrix unit."""
        if not hasattr(cpu, "vector") or not hasattr(cpu, "matrix"):
            raise TypeError("CPU does not expose Coreless vector/matrix state")
        self.cpu = cpu
        return self

    def add(self, left: Tensor, right: Tensor) -> Tensor:
        if self.cpu is not None and left.shape == right.shape and len(left.shape) == 1:
            return self.vector_add(left, right)
        if self.cpu is not None and left.shape == right.shape and len(left.shape) == 2:
            rows, cols = left.shape
            values = []
            for row in range(rows):
                values.extend(self.vector_add(
                    Tensor.from_values((cols,), left.data[row * cols:(row + 1) * cols], dtype=left.dtype),
                    Tensor.from_values((cols,), right.data[row * cols:(row + 1) * cols], dtype=right.dtype),
                ).data)
            return Tensor.from_values(left.shape, values, dtype=left.dtype)
        return add(left, right)

    def matmul(self, left: Tensor, right: Tensor) -> Tensor:
        """Multiply tensors, using the Coreless matrix unit when supported."""
        if (
            self.cpu is not None
            and len(left.shape) == 2
            and len(right.shape) == 2
            and left.dtype == right.dtype
            and left.dtype in self._ELEMENT_TYPES
        ):
            return self.matrix_matmul(left, right)
        return matmul(left, right)

    def sub(self, left: Tensor, right: Tensor) -> Tensor:
        if self.cpu is not None and left.shape == right.shape and len(left.shape) == 1:
            return self.vector_sub(left, right)
        if self.cpu is not None and left.shape == right.shape and len(left.shape) == 2:
            rows, cols = left.shape
            values = []
            for row in range(rows):
                values.extend(self.vector_sub(
                    Tensor.from_values((cols,), left.data[row * cols:(row + 1) * cols], dtype=left.dtype),
                    Tensor.from_values((cols,), right.data[row * cols:(row + 1) * cols], dtype=right.dtype),
                ).data)
            return Tensor.from_values(left.shape, values, dtype=left.dtype)
        return sub(left, right)

    def mul(self, left: Tensor, right: Tensor) -> Tensor:
        if self.cpu is not None and left.shape == right.shape and len(left.shape) == 1:
            return self.vector_mul(left, right)
        if self.cpu is not None and left.shape == right.shape and len(left.shape) == 2:
            rows, cols = left.shape
            values = []
            for row in range(rows):
                values.extend(self.vector_mul(
                    Tensor.from_values((cols,), left.data[row * cols:(row + 1) * cols], dtype=left.dtype),
                    Tensor.from_values((cols,), right.data[row * cols:(row + 1) * cols], dtype=right.dtype),
                ).data)
            return Tensor.from_values(left.shape, values, dtype=left.dtype)
        return mul(left, right)

    def dot(self, left: Tensor, right: Tensor) -> float:
        if self.cpu is not None and len(left.shape) == 1 and left.shape == right.shape:
            return self.vector_dot(left, right)
        return dot(left, right)

    def relu(self, value: Tensor) -> Tensor:
        return relu(value)

    def exp(self, value: Tensor) -> Tensor:
        return Tensor.from_values(
            value.shape,
            (exp(v) for v in value.data),
            dtype=value.dtype,
        )

    def silu(self, value: Tensor) -> Tensor:
        return Tensor.from_values(
            value.shape,
            (v / (1.0 + exp(-v)) for v in value.data),
            dtype=value.dtype,
        )

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

    def _vector_binary_native(self, left: Tensor, right: Tensor, op: int) -> Tensor:
        if left.size <= 64:
            return self._vector_binary_tile(left, right, op)
        values = []
        for start in range(0, left.size, 64):
            stop = min(start + 64, left.size)
            values.extend(self._vector_binary_tile(
                Tensor.from_values((stop - start,), left.data[start:stop], dtype=left.dtype),
                Tensor.from_values((stop - start,), right.data[start:stop], dtype=right.dtype),
                op,
            ).data)
        return Tensor.from_values(left.shape, values, dtype=left.dtype)

    def _vector_binary_tile(self, left: Tensor, right: Tensor, op: int) -> Tensor:
        self._same_vector_inputs(left, right)
        cpu = self._require_cpu()
        et = self._element_type(left.dtype)
        saved = {r: cpu.vector[r][:] for r in (29, 30, 31)}
        old_vl, old_vstart, old_vtype = cpu.vector_vl, cpu.vector_vstart, cpu.vector_vtype
        try:
            cpu.vector[29][:left.size] = [self._encode_value(v, left.dtype) for v in left.data]
            cpu.vector[30][:right.size] = [self._encode_value(v, right.dtype) for v in right.data]
            cpu.vector_vl, cpu.vector_vstart, cpu.vector_vtype = left.size, 0, et
            cpu.execute_vector(op, 31, 29, 30, et << 29)
            values = [self._decode_value(cpu.vector[31][i], left.dtype) for i in range(left.size)]
            return Tensor.from_values(left.shape, values, dtype=left.dtype)
        finally:
            for r, values in saved.items():
                cpu.vector[r][:] = values
            cpu.vector_vl, cpu.vector_vstart, cpu.vector_vtype = old_vl, old_vstart, old_vtype

    def vector_add(self, left: Tensor, right: Tensor) -> Tensor:
        return self._vector_binary(left, right, 0x00)

    def vector_sub(self, left: Tensor, right: Tensor) -> Tensor:
        return self._vector_binary_native(left, right, 0x01)

    def vector_mul(self, left: Tensor, right: Tensor) -> Tensor:
        return self._vector_binary(left, right, 0x02)

    def _vector_binary(self, left: Tensor, right: Tensor, op: int) -> Tensor:
        return self._vector_binary_native(left, right, op)

    def vector_dot(self, left: Tensor, right: Tensor) -> float:
        """Multiply through the Coreless vector unit, then reduce deterministically."""
        self._same_vector_inputs(left, right)
        if self.cpu is None:
            return fsum(self.vector_mul(left, right).data)
        return fsum(self._vector_binary_native(left, right, 0x02).data)

    def matrix_matmul(self, left: Tensor, right: Tensor) -> Tensor:
        if len(left.shape) != 2 or len(right.shape) != 2:
            raise ValueError("native matrix execution requires rank-2 tensors")
        if left.shape[1] != right.shape[0]:
            raise ValueError("matrix dimensions do not agree")
        if left.dtype != right.dtype or left.dtype not in self._ELEMENT_TYPES:
            raise ValueError("native Coreless matrix execution requires matching supported dtypes")
        if left.shape[0] == 0 or right.shape[1] == 0 or left.shape[1] == 0:
            raise ValueError("native matrix execution requires non-empty dimensions")
        shape = left.shape[0], right.shape[1], left.shape[1]
        if max(left.shape + right.shape) > self._MATRIX_TILE or shape not in self._MATRIX_SHAPES:
            return self._tiled_matrix_matmul(left, right)
        if shape not in self._MATRIX_SHAPES:
            raise ValueError("matrix shape is not supported by the Coreless baseline")
        cpu = self._require_cpu()
        et = self._element_type(left.dtype)
        shape_index = self._MATRIX_SHAPES.index(shape)
        saved = {r: [row[:] for row in cpu.matrix[r]] for r in (29, 30, 31)}
        old_shape = cpu.matrix_shape
        try:
            for i in range(left.shape[0]):
                for j in range(left.shape[1]):
                    cpu.matrix[29][i][j] = self._encode_value(left.at(i, j), left.dtype)
            for i in range(right.shape[0]):
                for j in range(right.shape[1]):
                    cpu.matrix[30][i][j] = self._encode_value(right.at(i, j), right.dtype)
            cpu.matrix_shape = shape
            cpu.execute_matrix(
                0x00, 31, 29, 30,
                (et << 29) | (et << 26) | (shape_index << 23) | (1 << 22),
                0, 0,
            )
            values = [self._decode_value(cpu.matrix[31][i][j], left.dtype)
                      for i in range(shape[0]) for j in range(shape[1])]
            return Tensor.from_values((shape[0], shape[1]), values, dtype=left.dtype)
        finally:
            for r, rows in saved.items():
                cpu.matrix[r][:] = rows
            cpu.matrix_shape = old_shape

    def _tiled_matrix_matmul(self, left: Tensor, right: Tensor) -> Tensor:
        """Execute arbitrarily sized 2-D matmul as Coreless-native 16x16 tiles."""
        m, k, n = left.shape[0], left.shape[1], right.shape[1]
        tile = self._MATRIX_TILE
        out = [0.0] * (m * n)
        for i0 in range(0, m, tile):
            im = min(tile, m - i0)
            for j0 in range(0, n, tile):
                jn = min(tile, n - j0)
                block = [0.0] * (im * jn)
                for k0 in range(0, k, tile):
                    kk = min(tile, k - k0)
                    a = [0.0] * (tile * tile)
                    b = [0.0] * (tile * tile)
                    for i in range(im):
                        for q in range(kk):
                            a[i * tile + q] = left.at(i0 + i, k0 + q)
                    for q in range(kk):
                        for j in range(jn):
                            b[q * tile + j] = right.at(k0 + q, j0 + j)
                    partial = self.matrix_matmul(
                        Tensor.from_values((tile, tile), a, dtype=left.dtype),
                        Tensor.from_values((tile, tile), b, dtype=right.dtype),
                    )
                    for i in range(im):
                        for j in range(jn):
                            block[i * jn + j] += partial.at(i, j)
                for i in range(im):
                    for j in range(jn):
                        out[(i0 + i) * n + j0 + j] = block[i * jn + j]
        return Tensor.from_values((m, n), out, dtype=left.dtype)

    def save(self, name: str, value: Tensor) -> str:
        if self.storage is None:
            raise RuntimeError("tensor runtime has no persistent storage")
        if not name or "/" in name:
            raise ValueError("tensor name must be a non-empty local name")
        key = f"{self.namespace}/{name}"
        payload = json.dumps(
            {"version": 2, "shape": list(value.shape), "dtype": value.dtype, "data": list(value.data)},
            separators=(",", ":"), sort_keys=True,
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
