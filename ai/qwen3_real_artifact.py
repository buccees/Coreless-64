"""Acquire, validate, and run a real Qwen3 artifact with Coreless."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .qwen3_artifact import (
    download_qwen3_06b,
    require_qwen3_06b_files,
)
from .qwen3_generation import Qwen3Generator
from .qwen3_model import load_qwen3_model
from .qwen3_tokenizer import load_qwen3_tokenizer


def run(model_directory: str | Path, prompt: str, max_new_tokens: int) -> str:
    root = Path(model_directory)
    require_qwen3_06b_files(root)
    runtime = load_qwen3_model(root)
    tokenizer = load_qwen3_tokenizer(
        root, expected_vocab_size=runtime.config.vocab_size
    )
    generator = Qwen3Generator(runtime, tokenizer)
    return generator.generate(prompt, max_new_tokens)


def acquire_and_run(
    model_directory: str | Path,
    prompt: str,
    max_new_tokens: int,
) -> str:
    root = download_qwen3_06b(model_directory)
    return run(root, prompt, max_new_tokens)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Acquire and run native Coreless Qwen3 inference"
    )
    parser.add_argument("model_directory")
    parser.add_argument("--prompt", default="Hello")
    parser.add_argument("--max-new-tokens", type=int, default=1)
    parser.add_argument(
        "--download",
        action="store_true",
        help="acquire the official Qwen3-0.6B artifact before running",
    )
    args = parser.parse_args()

    started = time.monotonic()
    if args.download:
        output = acquire_and_run(
            args.model_directory, args.prompt, args.max_new_tokens
        )
    else:
        output = run(args.model_directory, args.prompt, args.max_new_tokens)
    elapsed = time.monotonic() - started
    print(output)
    print(f"elapsed_seconds={elapsed:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
