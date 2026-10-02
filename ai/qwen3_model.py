"""Storage-backed Qwen3 model construction.

The loader validates the native artifact contract first, then exposes the
same storage-backed ModelWeights directly to the native Qwen3 runtime.
"""

from __future__ import annotations

from pathlib import Path

from .model_loader import load_model_weights_mmap
from .qwen3 import Qwen3Config, Qwen3Runtime
from .qwen3_loader import load_qwen3_config, validate_qwen3_artifact
from .tensor_runtime import TensorRuntime


def load_qwen3_model(
    directory: str | Path,
    tensor_runtime: TensorRuntime | None = None,
) -> Qwen3Runtime:
    root = Path(directory)
    validate_qwen3_artifact(root)
    config = load_qwen3_config(root / "config.json")
    weights = load_model_weights_mmap(root)
    return Qwen3Runtime(config, weights, tensor_runtime)
