import json

from qwen3_tokenizer import load_qwen3_tokenizer


def _write_tokenizer(tmp_path):
    vocab = {
        "h": 0,
        "e": 1,
        "l": 2,
        "o": 3,
        "he": 4,
        "hel": 5,
        "hell": 6,
        "hello": 7,
        "<|im_start|>": 8,
    }
    data = {
        "model": {
            "type": "BPE",
            "vocab": vocab,
            "merges": [["h", "e"], ["he", "l"], ["hel", "l"], ["hell", "o"]],
        },
        "added_tokens": [
            {"id": 8, "content": "<|im_start|>", "special": True},
        ],
    }
    (tmp_path / "tokenizer.json").write_text(json.dumps(data), encoding="utf-8")


def test_qwen3_tokenizer_artifact_loads_native_vocab(tmp_path):
    _write_tokenizer(tmp_path)
    tokenizer = load_qwen3_tokenizer(tmp_path, expected_vocab_size=9)
    assert tokenizer.model_type == "BPE"
    assert tokenizer.vocab["hello"] == 7
    assert tokenizer.vocab_size == 9


def test_qwen3_tokenizer_encodes_and_decodes_byte_level_bpe(tmp_path):
    _write_tokenizer(tmp_path)
    tokenizer = load_qwen3_tokenizer(tmp_path)
    assert tokenizer.encode("hello") == [7]
    assert tokenizer.decode([7]) == "hello"


def test_qwen3_tokenizer_preserves_special_tokens(tmp_path):
    _write_tokenizer(tmp_path)
    tokenizer = load_qwen3_tokenizer(tmp_path)
    assert tokenizer.encode("<|im_start|>hello") == [8, 7]
    assert tokenizer.decode([8, 7]) == "<|im_start|>hello"


def test_qwen3_tokenizer_applies_nfc_normalization(tmp_path):
    data = {
        "model": {
            "type": "BPE",
            "vocab": {"é": 0},
            "merges": [],
        }
    }
    (tmp_path / "tokenizer.json").write_text(json.dumps(data), encoding="utf-8")
    tokenizer = load_qwen3_tokenizer(tmp_path)
    assert tokenizer.encode("e\u0301") == [0]
