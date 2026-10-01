"""Qwen3 tokenizer artifact boundary.

The runtime does not silently substitute a different tokenizer. This module
validates and loads the native Hugging Face tokenizer vocabulary metadata so
tokenization can be added without changing the Qwen3 model architecture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Qwen3TokenizerArtifact:
    vocab_size: int
    model_type: str
    vocab: dict[str, int]

    @classmethod
    def load(cls, path: str | Path, expected_vocab_size: int | None = None) -> "Qwen3TokenizerArtifact":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("tokenizer artifact must be a JSON object")
        model = data.get("model")
        if not isinstance(model, dict):
            raise ValueError("tokenizer model metadata is missing")
        vocab = model.get("vocab")
        if not isinstance(vocab, dict) or not vocab:
            raise ValueError("tokenizer vocabulary is missing")
        normalized = {str(token): int(index) for token, index in vocab.items()}
        if len(set(normalized.values())) != len(normalized):
            raise ValueError("tokenizer vocabulary contains duplicate token IDs")
        max_id = max(normalized.values())
        vocab_size = max_id + 1
        if expected_vocab_size is not None and vocab_size > expected_vocab_size:
            raise ValueError("tokenizer vocabulary exceeds Qwen3 model vocabulary")
        return cls(vocab_size=vocab_size, model_type=str(model.get("type", "")), vocab=normalized)


def load_qwen3_tokenizer(model_directory: str | Path, expected_vocab_size: int | None = None) -> Qwen3TokenizerArtifact:
    root = Path(model_directory)
    return Qwen3TokenizerArtifact.load(root / "tokenizer.json", expected_vocab_size)
