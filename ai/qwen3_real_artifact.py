"""Run the native Coreless Qwen3 runtime against a real model artifact.

The model directory is supplied externally and is never committed to Coreless.
This is an integration runner rather than a CI unit test because the official
Qwen3-0.6B artifact is about 1.5 GB.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .qwen3_generation import Qwen3Generator
from .qwen3_model import load_qwen3_model
from .qwen3_tokenizer import load_qwen3_tokenizer


def run(model_directory: str | Path, prompt: str, max_new_tokens: int) -> str:
    root = Path(model_directory)
    runtime = load_qwen3_model(root)
    tokenizer = load_qwen3_tokenizer(root, expected_vocab_size=runtime.config.vocab_size)
    generator = Qwen3Generator(runtime, tokenizer)
    return generator.generate(prompt, max_new_tokens)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run native Coreless Qwen3 inference")
    parser.add_argument("model_directory")
    parser.add_argument("--prompt", default="Hello")
    parser.add_argument("--max-new-tokens", type=int, default=1)
    args = parser.parse_args()

    started = time.monotonic()
    output = run(args.model_directory, args.prompt, args.max_new_tokens)
    elapsed = time.monotonic() - started
    print(output)
    print(f"elapsed_seconds={elapsed:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
