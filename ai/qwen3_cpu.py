"""Adapter that exposes native Qwen3 inference to Coreless CPU and AI boundaries.

The adapter keeps Qwen3's native architecture and routes tensor operations
through TensorRuntime. A machine-bound TensorRuntime can dispatch supported
operations to the actual Coreless CPU vector/matrix state.
"""
from __future__ import annotations

from typing import Any, Sequence

from .cpu_hardware import CPUModelExecutionAdapter
from .interfaces import AIRequest, AIResult
from .model_weights import ModelWeights
from .qwen3 import Qwen3Config, Qwen3Runtime
from .tensor_runtime import TensorRuntime


class Qwen3CPUAdapter(CPUModelExecutionAdapter):
    """Execute Qwen3 inference through CPU-role and machine AI interfaces."""

    def __init__(
        self,
        config: Qwen3Config,
        weights: ModelWeights,
        tensor_runtime: TensorRuntime,
        tokenizer: Any | None = None,
    ) -> None:
        if tensor_runtime.cpu is None:
            raise ValueError("Qwen3 CPU adapter requires a TensorRuntime bound to a Coreless CPU")
        self.tensor_runtime = tensor_runtime
        self.runtime = Qwen3Runtime(config, weights, self.tensor_runtime)
        self.tokenizer = tokenizer

    @property
    def model_id(self) -> str:
        return "qwen3"

    def execute_cpu(self, operation: str, payload: Any) -> Any:
        if operation not in ("infer", "cpu.infer"):
            raise ValueError(f"unsupported Qwen3 CPU operation: {operation}")
        if not isinstance(payload, Sequence) or isinstance(
            payload, (str, bytes, bytearray)
        ):
            raise TypeError("Qwen3 CPU inference payload must be a token-id sequence")
        return self.runtime.forward([int(token) for token in payload])

    def infer(self, request: AIRequest) -> AIResult:
        """Run one scheduler-routed inference request.

        Callers may provide token_ids in request context for already-tokenized
        requests. Otherwise a compatible Qwen3 tokenizer must be configured.
        """
        token_ids = request.context.get("token_ids")
        if token_ids is None:
            if self.tokenizer is None:
                raise ValueError(
                    "Qwen3 AI request requires context token_ids or a configured tokenizer"
                )
            token_ids = self.tokenizer.encode(request.prompt)
        if not isinstance(token_ids, Sequence) or isinstance(
            token_ids, (str, bytes, bytearray)
        ):
            raise TypeError("Qwen3 request token_ids must be a sequence")
        normalized = [int(token) for token in token_ids]
        logits = self.runtime.forward(normalized)
        row = logits.data[-self.runtime.config.vocab_size:]
        next_token_id = max(range(len(row)), key=row.__getitem__)
        if self.tokenizer is not None:
            text = self.tokenizer.decode([next_token_id])
        else:
            text = str(next_token_id)
        return AIResult(
            request_id=request.request_id,
            model_id=self.model_id,
            text=text,
            metadata={
                "runtime": "native-qwen3",
                "input_tokens": len(normalized),
                "logit_shape": logits.shape,
                "next_token_id": next_token_id,
            },
        )
