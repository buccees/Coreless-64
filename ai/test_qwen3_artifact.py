from pathlib import Path

import pytest

from qwen3_artifact import (
    QWEN3_06B_REVISION,
    _url,
    require_qwen3_06b_files,
    sha256_file,
)


def test_qwen3_artifact_uses_immutable_revision():
    assert len(QWEN3_06B_REVISION) == 40
    assert _url("config.json").endswith(
        f"/{QWEN3_06B_REVISION}/config.json"
    )


def test_sha256_file(tmp_path: Path):
    path = tmp_path / "sample.bin"
    path.write_bytes(b"coreless")
    assert sha256_file(path) == (
        "d7e7a9c6d7f2a4e9b8b5d0c1a7f3c4c6b5d7e6f1a9d2c3b4e5f60718293a4b5c"
    )


def test_require_qwen3_06b_files_reports_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        require_qwen3_06b_files(tmp_path)
