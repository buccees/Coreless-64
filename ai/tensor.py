"""Deterministic Coreless tensor runtime foundation.

This layer maps tensor operations onto the architectural vector/matrix model
without making Python, PyTorch, or a remote AI service part of the ISA.
It is intentionally small and dependency-free so it can later be backed by
native Coreless vector/matrix instructions.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, fsum, sqrt
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Tensor:
    """Immutable dense tensor represented in row-major flat storage."""

    shape: tuple[int, ...]
    data: tuple[float, ...]
    dtype: str = "fp64"

    def __post_init__(self) -> None:
        if not self.shape or any(d <= 0 for d in self.shape):
            raise ValueError("tensor shape must contain positive dimensions")
        if self.dtype not in {"fp16", "bf16", "fp32", "fp64", "int8", "int16", "int32", "int64"}:
            raise ValueError("unsupported tensor dtype")
        size = 1
        for dim in self.shape:
            size *= dim
        if len(self.data) != size:
            raise ValueError("tensor data does not match tensor shape")

    @classmethod
    def from_values(cls, shape: Sequence[int], values: Iterable[float], dtype: str = "fp64") -> "Tensor":
        return cls(tuple(shape), tuple(float(v) for v in values), dtype)

    @property
    def size(self) -> int:
        return len(self.data)

    def _offset(self, indices: Sequence[int]) -> int:
        if len(indices) != len(self.shape):
            raise IndexError("wrong tensor rank")
        offset = 0
        for index, dim in zip(indices, self.shape):
            if not 0 <= index < dim:
                raise IndexError("tensor index out of range")
            offset = offset * dim + index
        return offset

    def at(self, *indices: int) -> float:
        return self.data[self._offset(indices)]

    def map(self, fn) -> "Tensor":
        return Tensor(self.shape, tuple(float(fn(x)) for x in self.data), self.dtype)

    def sum(self) -> float:
        return fsum(self.data)

    def mean(self) -> float:
        return self.sum() / self.size

    def l2_norm(self) -> float:
        return sqrt(fsum(x * x for x in self.data))

    def normalize(self, epsilon: float = 1e-12) -> "Tensor":
        if epsilon <= 0:
            raise ValueError("epsilon must be positive")
        norm = self.l2_norm()
        if norm <= epsilon:
            return Tensor(self.shape, tuple(0.0 for _ in self.data), self.dtype)
        return Tensor(self.shape, tuple(x / norm for x in self.data), self.dtype)


def matmul(a: Tensor, b: Tensor) -> Tensor:
    """Matrix multiplication using the Coreless matrix-runtime contract."""
    if len(a.shape) != 2 or len(b.shape) != 2:
        raise ValueError("matmul currently requires rank-2 tensors")
    rows, inner = a.shape
    other_inner, cols = b.shape
    if inner != other_inner:
        raise ValueError("matmul dimensions do not agree")
    values = []
    for row in range(rows):
        for col in range(cols):
            values.append(fsum(a.at(row, k) * b.at(k, col) for k in range(inner)))
    return Tensor((rows, cols), tuple(values))


def add(a: Tensor, b: Tensor) -> Tensor:
    if a.shape != b.shape:
        raise ValueError("tensor shapes must match")
    return Tensor(a.shape, tuple(x + y for x, y in zip(a.data, b.data)))


def relu(a: Tensor) -> Tensor:
    return a.map(lambda x: x if x > 0 else 0.0)


def softmax(a: Tensor) -> Tensor:
    if len(a.shape) != 1:
        raise ValueError("softmax currently requires a rank-1 tensor")
    maximum = max(a.data)
    values = tuple(exp(x - maximum) for x in a.data)
    total = sum(values)
    return Tensor(a.shape, tuple(x / total for x in values))


def linear(x: Tensor, weights: Tensor, bias: Tensor | None = None) -> Tensor:
    result = matmul(x, weights)
    if bias is not None:
        result = add(result, bias)
    return result


def sub(a: Tensor, b: Tensor) -> Tensor:
    if a.shape != b.shape:
        raise ValueError("tensor shapes must match")
    return Tensor(a.shape, tuple(x - y for x, y in zip(a.data, b.data)), a.dtype)


def mul(a: Tensor, b: Tensor) -> Tensor:
    if a.shape != b.shape:
        raise ValueError("tensor shapes must match")
    return Tensor(a.shape, tuple(x * y for x, y in zip(a.data, b.data)), a.dtype)


def dot(a: Tensor, b: Tensor) -> float:
    if a.size != b.size:
        raise ValueError("dot product requires equal tensor sizes")
    return fsum(x * y for x, y in zip(a.data, b.data))
