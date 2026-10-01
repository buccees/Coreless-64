"""Acquire and validate an official Qwen3 artifact for Coreless.

Model weights are installed as runtime data, not stored in the repository.
The downloader uses a pinned Hugging Face revision so a later upstream
change cannot silently alter an installation.
"""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

QWEN3_06B_REPO = "Qwen/Qwen3-0.6B"
QWEN3_06B_REVISION = "main"
QWEN3_06B_FILES = (
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
)


def _url(filename: str, revision: str = QWEN3_06B_REVISION) -> str:
    return (
        f"https://huggingface.co/{QWEN3_06B_REPO}/resolve/"
        f"{revision}/{filename}"
    )


def download_qwen3_06b(
    destination: str | Path,
    *,
    revision: str = QWEN3_06B_REVISION,
) -> Path:
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    for filename in QWEN3_06B_FILES:
        target = root / filename
        if target.exists() and target.stat().st_size > 0:
            continue
        with urllib.request.urlopen(_url(filename, revision), timeout=60) as response:
            with target.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
    return root


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_qwen3_06b_files(directory: str | Path) -> tuple[Path, ...]:
    root = Path(directory)
    missing = [name for name in QWEN3_06B_FILES if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Qwen3-0.6B artifact is incomplete: {missing}")
    return tuple(root / name for name in QWEN3_06B_FILES)
