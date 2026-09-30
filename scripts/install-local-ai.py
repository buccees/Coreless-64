#!/usr/bin/env python3
"""Prepare the Coreless local-AI configuration.

This script deliberately does not download model weights. Model servers and
weights are runtime/environment concerns, while Coreless owns the AI-Core
interface and policy boundary.

For a local OpenAI-compatible server, set CORELESS_LOCAL_AI_ENDPOINT and the
five CORELESS_*_MODEL variables if its model names differ from the defaults.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.local-ai.example"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare and optionally install Coreless local AI models.")
    parser.add_argument("--pull", action="store_true", help="Pull the configured models with Ollama.")
    args = parser.parse_args()

    endpoint = os.getenv(
        "CORELESS_LOCAL_AI_ENDPOINT",
        "http://127.0.0.1:11434/v1",
    )
    content = f"""# Coreless local AI runtime
CORELESS_LOCAL_AI_ENDPOINT={endpoint}
CORELESS_QWEN3_MODEL={os.getenv("CORELESS_QWEN3_MODEL", "qwen3")}
CORELESS_DEEPSEEK_MODEL={os.getenv("CORELESS_DEEPSEEK_MODEL", "deepseek-r1")}
CORELESS_GPT_OSS_MODEL={os.getenv("CORELESS_GPT_OSS_MODEL", "gpt-oss:20b")}
CORELESS_GEMMA_MODEL={os.getenv("CORELESS_GEMMA_MODEL", "gemma3")}
CORELESS_CODESTRAL_MODEL={os.getenv("CORELESS_CODESTRAL_MODEL", "codestral")}
"""
    ENV_EXAMPLE.write_text(content, encoding="utf-8")
    print(f"Wrote {ENV_EXAMPLE}")
    print("Start an OpenAI-compatible local model server, then use these settings.")
    print("No API key is required by the Coreless local adapter unless your local server requires one.")

    if args.pull:
        ollama = shutil.which("ollama")
        if ollama is None:
            raise SystemExit("Ollama was not found on PATH; install Ollama first or omit --pull.")
        models = [
            os.getenv("CORELESS_QWEN3_MODEL", "qwen3"),
            os.getenv("CORELESS_DEEPSEEK_MODEL", "deepseek-r1"),
            os.getenv("CORELESS_GPT_OSS_MODEL", "gpt-oss:20b"),
            os.getenv("CORELESS_GEMMA_MODEL", "gemma3"),
            os.getenv("CORELESS_CODESTRAL_MODEL", "codestral"),
        ]
        for model in models:
            print(f"Pulling {model} ...")
            subprocess.run([ollama, "pull", model], check=True)
        print("All configured local Coreless models are installed in Ollama.")


if __name__ == "__main__":
    main()
