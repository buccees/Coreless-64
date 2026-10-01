from ai.model_architecture import TransformerConfig
from ai.model_weights import ModelTensor, ModelWeights
from ai.tensor import Tensor
from ai.transformer import TransformerRuntime, embedding, scaled_dot_product_attention


def _weights() -> ModelWeights:
    def t(name, shape, values):
        return ModelTensor(name, Tensor.from_values(shape, values))
    return ModelWeights([
        t("embedding", (3, 2), [1, 0, 0, 1, 1, 1]),
        t("layers.0.input_norm", (2,), [1, 1]),
        t("layers.0.q_proj", (2, 2), [1, 0, 0, 1]),
        t("layers.0.k_proj", (2, 2), [1, 0, 0, 1]),
        t("layers.0.v_proj", (2, 2), [1, 0, 0, 1]),
        t("layers.0.o_proj", (2, 2), [1, 0, 0, 1]),
        t("layers.0.post_norm", (2,), [1, 1]),
        t("layers.0.ffn_up", (2, 2), [1, 0, 0, 1]),
        t("layers.0.ffn_down", (2, 2), [1, 0, 0, 1]),
        t("final_norm", (2,), [1, 1]),
        t("lm_head", (3, 2), [1, 0, 0, 1, 1, 1]),
    ])


def test_embedding_reads_vocabulary_rows():
    result = embedding([2, 0], _weights().get("embedding"))
    assert result.data == (1.0, 1.0, 1.0, 0.0)


def test_causal_attention_blocks_future_positions():
    q = Tensor.from_values((2, 2), [1, 0, 0, 1])
    k = Tensor.from_values((2, 2), [1, 0, 0, 1])
    v = Tensor.from_values((2, 1), [10, 20])
    result = scaled_dot_product_attention(q, k, v, causal=True)
    assert result.at(0, 0) == 10.0
    assert 10.0 < result.at(1, 0) < 20.0


def test_transformer_runtime_produces_vocab_logits():
    config = TransformerConfig(2, 2, 1, 1, 3, 8)
    logits = TransformerRuntime(config, _weights()).next_token_logits([0, 1])
    assert logits.shape == (3,)
    assert len(logits.data) == config.vocab_size


def test_transformer_rejects_context_overflow():
    runtime = TransformerRuntime(
        TransformerConfig(2, 2, 1, 1, 3, 1), _weights()
    )
    try:
        runtime.forward([0, 1])
    except ValueError:
        pass
    else:
        raise AssertionError("context overflow must fail")
