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



def validate_real_artifact(model_directory: str | Path) -> dict[str, object]:
    """Load only the artifact metadata and return the validated runtime shape."""
    root = Path(model_directory)
    require_qwen3_06b_files(root)
    runtime = load_qwen3_model(root)
    return {
        "model": "Qwen3-0.6B",
        "vocab_size": runtime.config.vocab_size,
        "hidden_size": runtime.config.hidden_size,
        "layers": runtime.config.num_hidden_layers,
        "attention_heads": runtime.config.num_attention_heads,
        "kv_heads": runtime.config.num_key_value_heads,
    }

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
