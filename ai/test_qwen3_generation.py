from qwen3_generation import Qwen3Generator


class FakeLogits:
    def __init__(self, rows):
        self.shape = (len(rows), len(rows[0]))
        self.data = tuple(value for row in rows for value in row)


class FakeRuntime:
    class Config:
        vocab_size = 4

    config = Config()

    def __init__(self):
        self.calls = []

    def forward(self, token_ids, cache=None):
        self.calls.append((tuple(token_ids), cache is not None))
        return FakeLogits([[0.0, 1.0, 0.0, 0.0]])


class FakeTokenizer:
    vocab_size = 4

    def encode(self, text):
        return [1]

    def decode(self, token_ids):
        return "generated"


def test_greedy_generation_appends_highest_logit():
    runtime = FakeRuntime()
    result = Qwen3Generator(runtime, FakeTokenizer()).generate_ids([1], 2)
    assert result == [1, 1, 1]
    assert runtime.calls == [((1,), True), ((1,), True)]


def test_text_generation_uses_native_tokenizer_boundary():
    runtime = FakeRuntime()
    result = Qwen3Generator(runtime, FakeTokenizer()).generate("hello", 1)
    assert result == "generated"
