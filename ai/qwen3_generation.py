"""Text generation boundary for the native Qwen3 runtime.

This is deliberately a small greedy-generation layer. It composes the native
Qwen3 tokenizer and runtime without introducing a different model family or
sampling implementation.
"""

from __future__ import annotations

from pathlib import Path

from .qwen3 import Qwen3Runtime
from .qwen3_tokenizer import Qwen3TokenizerArtifact


class Qwen3Generator:
    def __init__(self, runtime: Qwen3Runtime, tokenizer: Qwen3TokenizerArtifact) -> None:
        self.runtime = runtime
        self.tokenizer = tokenizer
        if tokenizer.vocab_size > runtime.config.vocab_size:
            raise ValueError("tokenizer vocabulary exceeds Qwen3 model vocabulary")

    def generate_ids(self, token_ids: list[int], max_new_tokens: int) -> list[int]:
        if max_new_tokens < 0:
            raise ValueError("max_new_tokens must be non-negative")
        generated = list(token_ids)
        for _ in range(max_new_tokens):
            logits = self.runtime.forward(generated)
            width = logits.shape[1]
            row = logits.data[(logits.shape[0] - 1) * width:]
            next_token = max(range(width), key=row.__getitem__)
            generated.append(next_token)
        return generated

    def generate(self, text: str, max_new_tokens: int) -> str:
        token_ids = self.tokenizer.encode(text)
        generated = self.generate_ids(token_ids, max_new_tokens)
        return self.tokenizer.decode(generated)


def generate_qwen3_text(
    runtime: Qwen3Runtime,
    tokenizer: Qwen3TokenizerArtifact,
    text: str,
    max_new_tokens: int,
) -> str:
    return Qwen3Generator(runtime, tokenizer).generate(text, max_new_tokens)
