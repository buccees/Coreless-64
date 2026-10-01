from ai.tensor import Tensor
from ai.transformer import feed_forward, scaled_dot_product_attention, transpose


def test_transpose():
    x = Tensor.from_values((2, 3), [1, 2, 3, 4, 5, 6])
    assert transpose(x).data == (1.0, 4.0, 2.0, 5.0, 3.0, 6.0)


def test_scaled_dot_product_attention():
    q = Tensor.from_values((1, 2), [1, 0])
    k = Tensor.from_values((2, 2), [1, 0, 0, 1])
    v = Tensor.from_values((2, 2), [10, 0, 0, 20])
    result = scaled_dot_product_attention(q, k, v)
    assert result.shape == (1, 2)
    assert abs(result.data[0] - 6.6976) < 0.01
    assert abs(result.data[1] - 6.6048) < 0.01


def test_feed_forward():
    x = Tensor.from_values((1, 2), [1, 2])
    w_in = Tensor.from_values((2, 2), [1, 0, 0, 1])
    w_out = Tensor.from_values((2, 2), [2, 0, 0, 3])
    result = feed_forward(x, w_in, w_out)
    assert result.data == (2.0, 6.0)


def test_transformer_runtime_routes_tensor_math_through_coreless_tensor_runtime():
    from ai.model_architecture import TransformerConfig
    from ai.model_weights import ModelTensor, ModelWeights
    from ai.tensor_runtime import TensorRuntime
    from ai.transformer import TransformerRuntime

    identity = Tensor.from_values((2, 2), [1, 0, 0, 1])
    norm = Tensor.from_values((2,), [1, 1])
    weights = ModelWeights([
        ModelTensor("embedding", Tensor.from_values((2, 2), [1, 0, 0, 1])),
        ModelTensor("layers.0.input_norm", norm),
        ModelTensor("layers.0.q_proj", identity),
        ModelTensor("layers.0.k_proj", identity),
        ModelTensor("layers.0.v_proj", identity),
        ModelTensor("layers.0.o_proj", identity),
        ModelTensor("layers.0.post_norm", norm),
        ModelTensor("layers.0.ffn_up", identity),
        ModelTensor("layers.0.ffn_down", identity),
        ModelTensor("final_norm", norm),
        ModelTensor("lm_head", identity),
    ])
    config = TransformerConfig(2, 2, 1, 1, 2, 4)
    runtime = TransformerRuntime(config, weights, TensorRuntime())
    result = runtime.next_token_logits([0, 1])
    assert result.shape == (2,)
    assert all(value == value for value in result.data)
