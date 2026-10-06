"""Coreless-native tensor execution and persistence boundary.

The runtime keeps tensor semantics independent of host ML frameworks. It can
execute deterministic dense operations and persist tensor values in the
Coreless machine image so model data can survive a power cycle.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from math import cos, exp, fsum, sin
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

    def last_row(self, value: Tensor) -> Tensor:
        """Select the final row of a rank-2 tensor without leaving TensorRuntime."""
        if len(value.shape) != 2:
            raise ValueError("last_row requires a rank-2 tensor")
        rows, width = value.shape
        if rows <= 0 or width <= 0:
            raise ValueError("last_row requires non-empty dimensions")
        start = (rows - 1) * width
        return Tensor.from_values((1, width), value.data[start:start + width], dtype=value.dtype)

    def last_row(self, value: Tensor) -> Tensor:
        """Select the final row of a rank-2 tensor without leaving TensorRuntime."""
        if len(value.shape) != 2:
            raise ValueError("last_row requires a rank-2 tensor")
        rows, width = value.shape
        if rows <= 0 or width <= 0:
            raise ValueError("last_row requires non-empty dimensions")
        start = (rows - 1) * width
        return Tensor.from_values((width,), value.data[start:start + width], dtype=value.dtype)

    def embedding_lookup(self, embedding: Tensor, token_ids: Iterable[int]) -> Tensor:
        """Gather token rows from a [vocab, hidden] embedding tensor."""
        if len(embedding.shape) != 2:
            raise ValueError("embedding_lookup requires a rank-2 embedding tensor")
        vocab, hidden = embedding.shape
        ids = tuple(int(token_id) for token_id in token_ids)
        if any(token_id < 0 or token_id >= vocab for token_id in ids):
            raise ValueError("token id is outside the embedding vocabulary")
        values = []
        for token_id in ids:
            start = token_id * hidden
            values.extend(embedding.data[start:start + hidden])
        return Tensor.from_values((len(ids), hidden), values, dtype=embedding.dtype)

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

    def reshape_heads(self, value: Tensor, heads: int, head_dim: int) -> Tensor:
        """Pack [positions, heads*head_dim] into [heads, positions, head_dim]."""
        if len(value.shape) != 2 or value.shape[1] != heads * head_dim:
            raise ValueError("reshape_heads requires a [positions, heads*head_dim] tensor")
        positions = value.shape[0]
        return Tensor.from_values(
            (heads, positions, head_dim),
            (value.at(pos, head * head_dim + dim)
             for head in range(heads) for pos in range(positions) for dim in range(head_dim)),
            dtype=value.dtype,
        )

    def repeat_heads(self, value: Tensor, repeats: int) -> Tensor:
        """Repeat the head axis for grouped-query attention without host lists."""
        if len(value.shape) != 3 or repeats <= 0:
            raise ValueError("repeat_heads requires a rank-3 tensor and positive repeats")
        heads, positions, head_dim = value.shape
        return Tensor.from_values(
            (heads * repeats, positions, head_dim),
            (value.at(head, pos, dim)
             for head in range(heads) for _ in range(repeats)
             for pos in range(positions) for dim in range(head_dim)),
            dtype=value.dtype,
        )

    def transpose_last_two(self, value: Tensor) -> Tensor:
        """Transpose the final two axes of a rank-3 attention tensor."""
        if len(value.shape) != 3:
            raise ValueError("transpose_last_two requires a rank-3 tensor")
        heads, rows, cols = value.shape
        return Tensor.from_values(
            (heads, cols, rows),
            (value.at(head, r, col)
             for head in range(heads) for col in range(cols) for r in range(rows)),
            dtype=value.dtype,
        )

    def sum_axis(self, value: Tensor, axis: int) -> Tensor:
        """Reduce a tensor by summing one axis using TensorRuntime storage."""
        rank = len(value.shape)
        if rank == 0:
            raise ValueError("sum_axis requires a non-scalar tensor")
        if axis < 0:
            axis += rank
        if axis < 0 or axis >= rank:
            raise ValueError("sum_axis axis out of range")
        if value.shape[axis] == 0:
            raise ValueError("sum_axis cannot reduce an empty axis")
        out_shape = value.shape[:axis] + value.shape[axis + 1:]
        if not out_shape:
            return Tensor.from_values((), (sum(value.data),), dtype=value.dtype)
        out_count = 1
        for size in out_shape:
            out_count *= size
        stride = 1
        for size in value.shape[axis + 1:]:
            stride *= size
        block = stride * value.shape[axis]
        values = []
        for out_index in range(out_count):
            base = (out_index // stride) * block + (out_index % stride)
            total = 0.0
            for item in range(value.shape[axis]):
                total += value.data[base + item * stride]
            values.append(total)
        return Tensor.from_values(out_shape, values, dtype=value.dtype)

    def batch_matmul(self, left: Tensor, right: Tensor) -> Tensor:
        """Execute independent rank-2 matrix products across an attention head axis."""
        if len(left.shape) != 3 or len(right.shape) != 3:
            raise ValueError("batch_matmul requires rank-3 tensors")
        if left.shape[0] != right.shape[0] or left.shape[2] != right.shape[1]:
            raise ValueError("batch matrix dimensions do not agree")
        heads, rows, inner = left.shape
        cols = right.shape[2]
        values = []
        for head in range(heads):
            a = Tensor.from_values((rows, inner),
                (left.at(head, r, k) for r in range(rows) for k in range(inner)),
                dtype=left.dtype)
            b = Tensor.from_values((inner, cols),
                (right.at(head, k, col) for k in range(inner) for col in range(cols)),
                dtype=right.dtype)
            values.extend(self.matmul(a, b).data)
        return Tensor.from_values((heads, rows, cols), values, dtype=left.dtype)

    def transpose(self, value: Tensor) -> Tensor:
        """Transpose a rank-2 tensor at the Coreless tensor boundary."""
        if len(value.shape) != 2:
            raise ValueError("transpose requires a rank-2 tensor")
        rows, cols = value.shape
        return Tensor.from_values(
            (cols, rows),
            (value.at(r, c) for c in range(cols) for r in range(rows)),
            dtype=value.dtype,
        )

    def mul_scalar(self, value: Tensor, scalar: float) -> Tensor:
        """Multiply every tensor element by a scalar through Coreless vector execution."""
        if self.cpu is not None and len(value.shape) in (1, 2):
            if len(value.shape) == 1:
                rhs = Tensor.from_values(
                    value.shape,
                    (scalar for _ in value.data),
                    dtype=value.dtype,
                )
                return self.vector_mul(value, rhs)
            rows, cols = value.shape
            values = []
            for row in range(rows):
                start = row * cols
                chunk = Tensor.from_values(
                    (cols,),
                    value.data[start:start + cols],
                    dtype=value.dtype,
                )
                rhs = Tensor.from_values(
                    (cols,),
                    (scalar for _ in range(cols)),
                    dtype=value.dtype,
                )
                values.extend(self.vector_mul(chunk, rhs).data)
            return Tensor.from_values(value.shape, values, dtype=value.dtype)
        return Tensor.from_values(
            value.shape,
            (v * scalar for v in value.data),
            dtype=value.dtype,
        )

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

    def reciprocal(self, value: Tensor) -> Tensor:
        """Elementwise reciprocal used by architecture-native normalization paths."""
        return Tensor.from_values(value.shape, (1.0 / v for v in value.data), dtype=value.dtype)

    def mean_square_rsqrt(self, value: Tensor, *, eps: float = 0.0) -> Tensor:
        """Reduce a vector to its RMS inverse without returning the scalar to host code."""
        if len(value.shape) != 1 or not value.data:
            raise ValueError("mean_square_rsqrt requires a non-empty rank-1 tensor")
        mean_square = fsum(v * v for v in value.data) / value.size
        return Tensor.from_values((1,), (1.0 / (mean_square + eps) ** 0.5,), dtype=value.dtype)

    def mul_broadcast(self, value: Tensor, scalar: Tensor) -> Tensor:
        """Multiply a tensor by a rank-1 single-value tensor through Coreless vector execution."""
        if scalar.shape != (1,):
            raise ValueError("mul_broadcast currently requires a single-value tensor")
        if not value.data:
            return Tensor.from_values(value.shape, (), dtype=value.dtype)
        if value.dtype != scalar.dtype:
            raise ValueError("mul_broadcast requires matching dtypes")
        rhs = Tensor.from_values(
            value.shape,
            (scalar.data[0] for _ in value.data),
            dtype=value.dtype,
        )
        return self.mul(value, rhs)

    def rms_norm_rows(self, value: Tensor, weight: Tensor, *, eps: float = 0.0) -> Tensor:
        """Apply RMSNorm across the final axis of a rank-2 tensor."""
        if len(value.shape) != 2:
            raise ValueError("rms_norm_rows requires a rank-2 tensor")
        if len(weight.shape) != 1 or weight.shape[0] != value.shape[1]:
            raise ValueError("row RMSNorm weight must match the final dimension")
        rows, dim = value.shape
        values = []
        for row in range(rows):
            start = row * dim
            chunk = Tensor.from_values((dim,), value.data[start:start + dim], dtype=value.dtype)
            values.extend(self.rms_norm(chunk, weight, eps=eps).data)
        return Tensor.from_values(value.shape, values, dtype=value.dtype)

    def rms_norm(self, value: Tensor, weight: Tensor, *, eps: float = 0.0) -> Tensor:
        """Normalize a vector and apply its learned RMS weight through Coreless primitives."""
        if len(value.shape) != 1 or not value.data:
            raise ValueError("rms_norm requires a non-empty rank-1 tensor")
        if weight.shape != value.shape:
            raise ValueError("rms_norm weight shape must match the input")
        scale = self.mean_square_rsqrt(value, eps=eps)
        scaled = self.mul_broadcast(value, scale)
        return self.mul(scaled, weight)

    def rsqrt(self, value: Tensor, *, eps: float = 0.0) -> Tensor:
        """Elementwise reciprocal square root with an explicit stability epsilon."""
        return Tensor.from_values(value.shape, (1.0 / (v + eps) ** 0.5 for v in value.data), dtype=value.dtype)

    def sin(self, value: Tensor) -> Tensor:
        """Elementwise sine at the Coreless tensor boundary."""
        return Tensor.from_values(value.shape, (sin(v) for v in value.data), dtype=value.dtype)

    def cos(self, value: Tensor) -> Tensor:
        """Elementwise cosine at the Coreless tensor boundary."""
        return Tensor.from_values(value.shape, (cos(v) for v in value.data), dtype=value.dtype)

    def rms_norm_heads(
        self,
        value: Tensor,
        weight: Tensor,
        *,
        eps: float = 0.0,
    ) -> Tensor:
        """Apply RMSNorm across the final axis of a rank-3 head tensor."""
        if len(value.shape) != 3:
            raise ValueError("rms_norm_heads requires a rank-3 tensor")
        if len(weight.shape) != 1 or weight.shape[0] != value.shape[-1]:
            raise ValueError("head RMSNorm weight must match the final dimension")
        heads, positions, dim = value.shape
        values = []
        for head in range(heads):
            for position in range(positions):
                start = (head * positions + position) * dim
                chunk = Tensor.from_values(
                    (dim,),
                    value.data[start:start + dim],
                    dtype=value.dtype,
                )
                values.extend(self.rms_norm(chunk, weight, eps=eps).data)
        return Tensor.from_values(value.shape, values, dtype=value.dtype)

    def append_sequence(self, existing: Tensor, update: Tensor) -> Tensor:
        """Append rank-3 sequence positions without leaving the TensorRuntime boundary."""
        if len(existing.shape) != 3 or len(update.shape) != 3:
            raise ValueError("append_sequence requires rank-3 tensors")
        if existing.shape[0] != update.shape[0] or existing.shape[2] != update.shape[2]:
            raise ValueError("sequence tensors must match head and feature dimensions")
        if existing.dtype != update.dtype:
            raise ValueError("sequence tensors must use matching dtypes")
        heads, old_positions, dim = existing.shape
        new_positions = update.shape[1]
        values = []
        for head in range(heads):
            old_start = head * old_positions * dim
            new_start = head * new_positions * dim
            values.extend(existing.data[old_start:old_start + old_positions * dim])
            values.extend(update.data[new_start:new_start + new_positions * dim])
        return Tensor.from_values(
            (heads, old_positions + new_positions, dim),
            values,
            dtype=existing.dtype,
        )

    def rotary_embedding(
        self,
        value: Tensor,
        *,
        position_offset: int = 0,
        theta: float = 1000000.0,
        scaling_factor: float | None = None,
    ) -> Tensor:
        """Apply RoPE across a [heads, positions, head_dim] tensor."""
        if len(value.shape) != 3:
            raise ValueError("rotary_embedding requires a rank-3 tensor")
        if position_offset < 0:
            raise ValueError("RoPE position offset must be non-negative")
        heads, positions, dim = value.shape
        if dim <= 0 or dim % 2:
            raise ValueError("rotary head dimension must be positive and even")
        half = dim // 2
        values = []
        for head in range(heads):
            for position in range(positions):
                angles = self.rope_angles(
                    half,
                    position_offset + position,
                    theta,
                    scaling_factor=scaling_factor,
                    dtype=value.dtype,
                )
                c = self.cos(angles)
                s = self.sin(angles)
                a = Tensor.from_values(
                    (half,),
                    (value.at(head, position, index) for index in range(half)),
                    dtype=value.dtype,
                )
                b = Tensor.from_values(
                    (half,),
                    (value.at(head, position, half + index) for index in range(half)),
                    dtype=value.dtype,
                )
                first = self.sub(self.mul(a, c), self.mul(b, s))
                second = self.add(self.mul(a, s), self.mul(b, c))
                values.extend(first.data)
                values.extend(second.data)
        return Tensor.from_values(value.shape, values, dtype=value.dtype)

    def rope_angles(
        self,
        half: int,
        position: int,
        theta: float,
        *,
        scaling_factor: float | None = None,
        dtype: str = "fp64",
    ) -> Tensor:
        """Generate the deterministic RoPE angle basis at the Coreless boundary."""
        if half <= 0:
            raise ValueError("RoPE angle basis requires a positive half dimension")
        if theta <= 0.0:
            raise ValueError("RoPE theta must be positive")
        scale = scaling_factor if scaling_factor is not None and scaling_factor > 1.0 else 1.0
        return Tensor.from_values(
            (half,),
            (position * theta ** (-2.0 * i / (half * 2)) / scale for i in range(half)),
            dtype=dtype,
        )

    def argmax(self, value: Tensor) -> int:
        """Return the deterministic flat index of the largest tensor element."""
        if not value.data:
            raise ValueError("argmax requires a non-empty tensor")
        return max(range(len(value.data)), key=value.data.__getitem__)

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

    def attention(self, q: Tensor, k: Tensor, v: Tensor, *, causal: bool = True, key_position_offset: int = 0) -> Tensor:
        """Execute scaled dot-product attention entirely inside TensorRuntime."""
        if len(q.shape) != 3 or len(k.shape) != 3 or len(v.shape) != 3:
            raise ValueError("attention tensors must be rank-3")
        if q.shape[0] != k.shape[0] or k.shape != v.shape:
            raise ValueError("attention head dimensions do not agree")
        dim = q.shape[2]
        if dim <= 0:
            raise ValueError("attention head dimension must be positive")
        scores = self.batch_matmul(q, self.transpose_last_two(k))
        scores = self.mul_scalar(scores, 1.0 / (dim ** 0.5))
        if causal:
            scores = self.masked_fill(
                scores,
                self.causal_mask(scores.shape, query_offset=key_position_offset, dtype=scores.dtype),
                float("-inf"),
            )
        probabilities = self.softmax_last_dim(scores)
        return self.sum_axis(self.batch_matmul(probabilities, v), 0)

    def softmax_last_dim(self, value: Tensor) -> Tensor:
        """Apply deterministic softmax independently across the final tensor axis."""
        if len(value.shape) < 2:
            return self.softmax(value)
        rows = value.size // value.shape[-1]
        width = value.shape[-1]
        outputs = []
        for row in range(rows):
            start = row * width
            outputs.extend(softmax(
                Tensor.from_values((width,), value.data[start:start + width], dtype=value.dtype)
            ).data)
        return Tensor.from_values(value.shape, outputs, dtype=value.dtype)

    def softmax(self, value: Tensor) -> Tensor:
        if len(value.shape) == 1:
            return softmax(value)
        if len(value.shape) == 2:
            rows, cols = value.shape
            values = []
            for row in range(rows):
                values.extend(
                    softmax(
                        Tensor.from_values(
                            (cols,),
                            value.data[row * cols:(row + 1) * cols],
                            dtype=value.dtype,
                        )
                    ).data
                )
            return Tensor.from_values(value.shape, values, dtype=value.dtype)
        return softmax(value)

    def causal_mask(self, shape: tuple[int, ...], query_offset: int = 0, dtype: str = "fp64") -> Tensor:
        """Build a causal attention mask across the final two axes."""
        if len(shape) < 2:
            raise ValueError("causal_mask requires at least two dimensions")
        rows, cols = shape[-2], shape[-1]
        prefix_count = 1
        for size in shape[:-2]:
            prefix_count *= size
        values = []
        for _ in range(prefix_count):
            for row in range(rows):
                for col in range(cols):
                    values.append(1.0 if col <= query_offset + row else 0.0)
        return Tensor.from_values(shape, values, dtype=dtype)

    def masked_fill(self, value: Tensor, mask: Tensor, fill_value: float) -> Tensor:
        """Apply an elementwise mask before architecture-level normalization."""
        if value.shape != mask.shape:
            raise ValueError("masked_fill requires matching tensor shapes")
        return Tensor.from_values(
            value.shape,
            (fill_value if bool(m) else v for v, m in zip(value.data, mask.data)),
            dtype=value.dtype,
        )

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
