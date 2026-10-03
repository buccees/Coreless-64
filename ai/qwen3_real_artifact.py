"""Acquire, validate, and run a real Qwen3 artifact with Coreless."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .qwen3_artifact import download_qwen3_06b, require_qwen3_06b_files
from .qwen3_generation import Qwen3Generator
from .qwen3_model import load_qwen3_model
from .qwen3_tokenizer import load_qwen3_tokenizer
from .tensor_runtime import TensorRuntime


def _load_real_artifact(model_directory: str | Path, tensor_runtime: TensorRuntime | None = None):
    root = Path(model_directory)
    require_qwen3_06b_files(root)
    runtime = load_qwen3_model(root, tensor_runtime=tensor_runtime)
    tokenizer = load_qwen3_tokenizer(
        root, expected_vocab_size=runtime.config.vocab_size
    )
    return root, runtime, tokenizer


def run(model_directory: str | Path, prompt: str, max_new_tokens: int, tensor_runtime: TensorRuntime | None = None) -> str:
    _, runtime, tokenizer = _load_real_artifact(model_directory, tensor_runtime)
    generator = Qwen3Generator(runtime, tokenizer)
    return generator.generate(prompt, max_new_tokens)


def acquire_and_run(
    model_directory: str | Path,
    prompt: str,
    max_new_tokens: int,
    tensor_runtime: TensorRuntime | None = None,
) -> str:
    root = download_qwen3_06b(model_directory)
    return run(root, prompt, max_new_tokens, tensor_runtime)


def forward_real_artifact(
    model_directory: str | Path,
    prompt: str,
    tensor_runtime: TensorRuntime | None = None,
) -> dict[str, object]:
    """Run one real trained-weight forward pass through the native runtime."""
    _, runtime, tokenizer = _load_real_artifact(model_directory, tensor_runtime)
    token_ids = tokenizer.encode(prompt)
    if not token_ids:
        raise ValueError("prompt must produce at least one token")
    logits = runtime.forward(token_ids)
    row = logits.data[-runtime.config.vocab_size:]
    next_token = max(range(len(row)), key=row.__getitem__)
    return {
        "model": "Qwen3-0.6B",
        "input_tokens": len(token_ids),
        "logit_shape": logits.shape,
        "next_token_id": next_token,
    }


def validate_real_artifact(model_directory: str | Path) -> dict[str, object]:
    """Validate the official model, storage layout, and native tokenizer."""
    _, runtime, tokenizer = _load_real_artifact(model_directory)
    return {
        "model": "Qwen3-0.6B",
        "vocab_size": runtime.config.vocab_size,
        "tokenizer_vocab_size": tokenizer.vocab_size,
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
    parser.add_argument("--native-cpu", action="store_true", help="bind inference to the native Coreless CPU")
    parser.add_argument("--prompt", default="Hello")
    parser.add_argument("--max-new-tokens", type=int, default=1)
    parser.add_argument(
        "--download",
        action="store_true",
        help="acquire the official Qwen3-0.6B artifact before running",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate model and tokenizer artifacts without inference",
    )
    parser.add_argument(
        "--forward-only",
        action="store_true",
        help="run one real trained-weight forward pass without generation",
    )
    args = parser.parse_args()

    started = time.monotonic()
    tensor_runtime = None
    if args.native_cpu:
        from core import CorelessCPU
        tensor_runtime = TensorRuntime(cpu=CorelessCPU())
    if args.download:
        root = download_qwen3_06b(args.model_directory)
    else:
        root = Path(args.model_directory)

    if args.validate_only:
        print(validate_real_artifact(root))
    elif args.forward_only:
        print(forward_real_artifact(root, args.prompt, tensor_runtime))
    else:
        print(run(root, args.prompt, args.max_new_tokens, tensor_runtime))
    elapsed = time.monotonic() - started
    print(f"elapsed_seconds={elapsed:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
