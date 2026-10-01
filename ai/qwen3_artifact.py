"""Acquire and validate an official Qwen3 artifact for Coreless.

Model weights are installed as runtime data, not stored in the repository.
The downloader uses an immutable Hugging Face revision and verifies the
published hash for the large model file before activation.
"""

from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path

QWEN3_06B_REPO = "Qwen/Qwen3-0.6B"
QWEN3_06B_REVISION = "167b8104f88905a951069f5f95f9776908da5f68"
QWEN3_06B_FILES = (
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
)

QWEN3_06B_SHA256 = {
    "model.safetensors": "f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874",
}


def _url(filename: str, revision: str = QWEN3_06B_REVISION) -> str:
    return (
        f"https://huggingface.co/{QWEN3_06B_REPO}/resolve/"
        f"{revision}/{filename}"
    )


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_file(path: Path, filename: str) -> None:
    expected = QWEN3_06B_SHA256.get(filename)
    if expected is not None and sha256_file(path) != expected:
        raise ValueError(f"Qwen3-0.6B checksum mismatch: {filename}")


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
            _verify_file(target, filename)
            continue

        temporary = target.with_name(target.name + ".part")
        try:
            with urllib.request.urlopen(_url(filename, revision), timeout=60) as response:
                with temporary.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
            _verify_file(temporary, filename)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    return root


def require_qwen3_06b_files(directory: str | Path) -> tuple[Path, ...]:
    root = Path(directory)
    missing = [name for name in QWEN3_06B_FILES if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Qwen3-0.6B artifact is incomplete: {missing}")
    for filename in QWEN3_06B_FILES:
        _verify_file(root / filename, filename)
    return tuple(root / name for name in QWEN3_06B_FILES)
