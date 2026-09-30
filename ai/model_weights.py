"""Deterministic model-weight representation for the Coreless AI runtime.

This is intentionally a format-neutral boundary: model loaders can translate
external formats into ModelWeights without making those formats ISA
dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ai.tensor import Tensor


@dataclass(frozen=True)
class ModelTensor:
    name: str
    tensor: Tensor


class ModelWeights:
    def __init__(self, tensors: Iterable[ModelTensor] = ()) -> None:
        self._tensors: dict[str, Tensor] = {}
        for item in tensors:
            self.add(item.name, item.tensor)

    def add(self, name: str, tensor: Tensor) -> None:
        if not name:
            raise ValueError("tensor name must not be empty")
        if name in self._tensors:
            raise ValueError(f"duplicate tensor: {name}")
        self._tensors[name] = tensor

    def get(self, name: str) -> Tensor:
        try:
            return self._tensors[name]
        except KeyError as exc:
            raise KeyError(f"unknown model tensor: {name}") from exc

    def contains(self, name: str) -> bool:
        return name in self._tensors

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tensors))

    def __len__(self) -> int:
        return len(self._tensors)
