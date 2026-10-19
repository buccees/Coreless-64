"""Adapter that exposes the native Qwen3 runtime as a Coreless CPU-role component.

Inference remains Qwen3-native. The adapter is the boundary between the model
runtime and the CPU hardware-role contract; it does not reinterpret Qwen3 as a
generic Transformer. TensorRuntime is always supplied because native Qwen3
attention and the other tensor operations must cross that explicit boundary.
"""
from __future__ import annotations

from typing import Any, Sequence

from .cpu_hardware import CPUModelExecutionAdapter
from .model_weights import ModelWeights
from .qwen3 import Qwen3Config, Qwen3Runtime
from .tensor_runtime import TensorRuntime


class Qwen3CPUAdapter(CPUModelExecutionAdapter):
    """Execute Qwen3 inference through a CPU-role hardware endpoint."""

    def __init__(
        self,
        config: Qwen3Config,
        weights: ModelWeights,
        tensor_runtime: TensorRuntime | None = None,
    ) -> None:
        self.tensor_runtime = tensor_runtime or TensorRuntime()
        self.runtime = Qwen3Runtime(config, weights, self.tensor_runtime)

    def execute_cpu(self, operation: str, payload: Any) -> Any:
        if operation not in ("infer", "cpu.infer"):
            raise ValueError(f"unsupported Qwen3 CPU operation: {operation}")
        if not isinstance(payload, Sequence) or isinstance(
            payload, (str, bytes, bytearray)
        ):
            raise TypeError("Qwen3 CPU inference payload must be a token-id sequence")
        return self.runtime.forward([int(token) for token in payload])
