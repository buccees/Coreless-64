from qwen3_cpu import Qwen3CPUAdapter
from qwen3 import Qwen3Config
from model_weights import ModelWeights, ModelTensor
from tensor import Tensor


def test_qwen3_cpu_adapter_requires_native_inference_operation():
    cfg = Qwen3Config(4, 8, 1, 2, 1, 16, 32)
    w = ModelWeights([
        ModelTensor("model.embed_tokens.weight", Tensor.from_values((16, 4), [0.0] * 64)),
        ModelTensor("model.layers.0.input_layernorm.weight", Tensor.from_values((4,), [1.0] * 4)),
        ModelTensor("model.layers.0.self_attn.q_proj.weight", Tensor.from_values((4, 4), [0.0] * 16)),
        ModelTensor("model.layers.0.self_attn.k_proj.weight", Tensor.from_values((2, 4), [0.0] * 8)),
        ModelTensor("model.layers.0.self_attn.v_proj.weight", Tensor.from_values((2, 4), [0.0] * 8)),
        ModelTensor("model.layers.0.self_attn.q_norm.weight", Tensor.from_values((2,), [1.0] * 2)),
        ModelTensor("model.layers.0.self_attn.k_norm.weight", Tensor.from_values((2,), [1.0] * 2)),
        ModelTensor("model.layers.0.self_attn.o_proj.weight", Tensor.from_values((4, 4), [0.0] * 16)),
        ModelTensor("model.layers.0.post_attention_layernorm.weight", Tensor.from_values((4,), [1.0] * 4)),
        ModelTensor("model.layers.0.mlp.gate_proj.weight", Tensor.from_values((8, 4), [0.0] * 32)),
        ModelTensor("model.layers.0.mlp.up_proj.weight", Tensor.from_values((8, 4), [0.0] * 32)),
        ModelTensor("model.layers.0.mlp.down_proj.weight", Tensor.from_values((4, 8), [0.0] * 32)),
        ModelTensor("model.norm.weight", Tensor.from_values((4,), [1.0] * 4)),
        ModelTensor("lm_head.weight", Tensor.from_values((16, 4), [0.0] * 64)),
    ])
    adapter = Qwen3CPUAdapter(cfg, w)
    result = adapter.execute_cpu("cpu.infer", [1])
    assert result.shape == (1, 16)


def test_qwen3_cpu_adapter_rejects_other_operations():
    cfg = Qwen3Config(4, 8, 1, 2, 1, 16, 32)
    w = ModelWeights()
    adapter = Qwen3CPUAdapter(cfg, w)
    try:
        adapter.execute_cpu("cpu.step", [])
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported operation was accepted")
