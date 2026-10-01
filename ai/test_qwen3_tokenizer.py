import json

from qwen3_tokenizer import load_qwen3_tokenizer


def test_qwen3_tokenizer_artifact_loads_native_vocab(tmp_path):
    data = {
        "model": {
            "type": "BPE",
            "vocab": {"<pad>": 0, "hello": 1, " world": 2},
        }
    }
    (tmp_path / "tokenizer.json").write_text(json.dumps(data))
    tokenizer = load_qwen3_tokenizer(tmp_path, expected_vocab_size=4)
    assert tokenizer.model_type == "BPE"
    assert tokenizer.vocab["hello"] == 1
    assert tokenizer.vocab_size == 3
