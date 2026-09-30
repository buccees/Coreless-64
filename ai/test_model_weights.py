from ai.model_weights import ModelTensor, ModelWeights
from ai.tensor import Tensor


def test_model_weights_are_named_and_deterministic():
    weights = ModelWeights([
        ModelTensor("layer.1", Tensor.from_values((1,), [2])),
        ModelTensor("layer.0", Tensor.from_values((1,), [1])),
    ])
    assert weights.names() == ("layer.0", "layer.1")
    assert weights.get("layer.1").data == (2.0,)


def test_duplicate_and_unknown_weights_fail():
    weights = ModelWeights()
    weights.add("x", Tensor.from_values((1,), [1]))
    try:
        weights.add("x", Tensor.from_values((1,), [2]))
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate tensor must fail")

    try:
        weights.get("missing")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown tensor must fail")
