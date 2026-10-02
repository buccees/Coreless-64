"""Opt-in numerical comparison between Coreless and Hugging Face Qwen3.

Set CORELESS_QWEN3_MODEL_DIR to a local official Qwen3-0.6B artifact and
install the optional reference dependencies before running this test.
"""

from __future__ import annotations

import os

import pytest

from qwen3_model import load_qwen3_model
from qwen3_tokenizer import load_qwen3_tokenizer


MODEL_DIR = os.environ.get("CORELESS_QWEN3_MODEL_DIR")
PROMPT = os.environ.get("CORELESS_QWEN3_REFERENCE_PROMPT", "Hello")


@pytest.mark.skipif(not MODEL_DIR, reason="real Qwen3 artifact not configured")
def test_qwen3_matches_huggingface_reference():
    torch = pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")

    tokenizer = load_qwen3_tokenizer(MODEL_DIR)
    native = load_qwen3_model(MODEL_DIR)
    token_ids = tokenizer.encode(PROMPT)
    assert token_ids

    native_logits = native.forward(token_ids)
    native_row = native_logits.data[-native.config.vocab_size:]
    native_next = max(range(len(native_row)), key=native_row.__getitem__)

    reference_tokenizer = transformers.AutoTokenizer.from_pretrained(
        MODEL_DIR, local_files_only=True
    )
    reference_model = transformers.AutoModelForCausalLM.from_pretrained(
        MODEL_DIR, local_files_only=True, torch_dtype=torch.float32
    )
    reference_model.eval()

    reference_ids = reference_tokenizer(
        PROMPT, return_tensors="pt"
    ).input_ids[0].tolist()
    assert reference_ids == token_ids

    with torch.no_grad():
        reference_logits = reference_model(
            input_ids=torch.tensor([token_ids], dtype=torch.long)
        ).logits[0, -1].float()

    reference_next = int(torch.argmax(reference_logits).item())
    assert native_next == reference_next

    max_abs_error = max(
        abs(float(native_row[index]) - float(reference_logits[index]))
        for index in range(native.config.vocab_size)
    )
    assert max_abs_error < 1e-2
