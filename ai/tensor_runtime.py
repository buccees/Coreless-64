"""Coreless-native tensor execution and persistence boundary.

The runtime keeps tensor semantics independent of host ML frameworks. It can
execute deterministic dense operations and persist tensor values in the
Coreless machine image so model data can survive a power cycle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from .tensor import Tensor, add, matmul, relu, softmax


@dataclass
class TensorRuntime:
    """Dependency-free tensor runtime bound to a Coreless storage image."""

    storage: object | None = None
    namespace: str = "tensor"

    def create(self, shape: Iterable[int], values: Iterable[float]) -> Tensor:
        return Tensor.from_values(tuple(shape), values)

    def add(self, left: Tensor, right: Tensor) -> Tensor:
        return add(left, right)

    def matmul(self, left: Tensor, right: Tensor) -> Tensor:
        return matmul(left, right)

    def relu(self, value: Tensor) -> Tensor:
        return relu(value)

    def softmax(self, value: Tensor) -> Tensor:
        return softmax(value)

    def save(self, name: str, value: Tensor) -> str:
        if self.storage is None:
            raise RuntimeError("tensor runtime has no persistent storage")
        if not name or "/" in name:
            raise ValueError("tensor name must be a non-empty local name")
        key = f"{self.namespace}/{name}"
        payload = json.dumps(
            {"version": 1, "shape": list(value.shape), "data": list(value.data)},
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
        if payload.get("version") != 1:
            raise ValueError("unsupported tensor format version")
        return Tensor.from_values(payload["shape"], payload["data"])
