"""Integration proof for the assigned Qwen3 CPU-AI execution path.

This test deliberately crosses the role assignment, CPU hardware bridge, native
Qwen3 adapter, model forward pass, and response boundary. Tiny deterministic
weights keep it offline and make the proof independent of downloading a model.
The official trained artifact remains a separate acceptance test.
"""
from ai.cpu_hardware import CorelessCPUBridge, CorelessCPUHardware
from ai.model_weights import ModelWeights
from ai.qwen3 import Qwen3Config
from ai.qwen3_cpu import Qwen3CPUAdapter
from ai.tensor import Tensor
from ai.hardware_runtime import HardwareRequest
from ai.model_part import (
    Capability,
    ComponentRole,
    HardwareAssignmentRegistry,
    ModelPart,
    RoleContract,
    TaskContract,
)


def _tiny_qwen3_weights():
    config = Qwen3Config(
        hidden_size=2,
        intermediate_size=2,
        num_hidden_layers=1,
        num_attention_heads=1,
        num_key_value_heads=1,
        vocab_size=3,
        max_position_embeddings=8,
        head_dim=2,
    )
    weights = ModelWeights()

    def add(name, shape, values):
        weights.add(name, Tensor.from_values(shape, values))

    add("model.embed_tokens.weight", (3, 2), (0.1, 0.2, 0.3, 0.4, 0.5, 0.6))
    add("model.norm.weight", (2,), (1.0, 1.0))
    prefix = "model.layers.0"
    add(f"{prefix}.input_layernorm.weight", (2,), (1.0, 1.0))
    add(f"{prefix}.post_attention_layernorm.weight", (2,), (1.0, 1.0))
    add(f"{prefix}.self_attn.q_proj.weight", (2, 2), (0.1, 0.0, 0.0, 0.1))
    add(f"{prefix}.self_attn.k_proj.weight", (2, 2), (0.1, 0.0, 0.0, 0.1))
    add(f"{prefix}.self_attn.v_proj.weight", (2, 2), (0.1, 0.0, 0.0, 0.1))
    add(f"{prefix}.self_attn.o_proj.weight", (2, 2), (0.1, 0.0, 0.0, 0.1))
    add(f"{prefix}.self_attn.q_norm.weight", (2,), (1.0, 1.0))
    add(f"{prefix}.self_attn.k_norm.weight", (2,), (1.0, 1.0))
    add(f"{prefix}.mlp.gate_proj.weight", (2, 2), (0.1, 0.0, 0.0, 0.1))
    add(f"{prefix}.mlp.up_proj.weight", (2, 2), (0.1, 0.0, 0.0, 0.1))
    add(f"{prefix}.mlp.down_proj.weight", (2, 2), (0.1, 0.0, 0.0, 0.1))
    return config, weights


def test_qwen3_cpu_role_executes_end_to_end_and_returns_verified_result():
    config, weights = _tiny_qwen3_weights()
    from machine_runtime import CorelessMachine
    machine = CorelessMachine(memory_size=4096)
    adapter = Qwen3CPUAdapter(config, weights, tensor_runtime=machine.tensor_runtime)

    role = RoleContract(
        role=ComponentRole.CPU,
        mandatory_capabilities=("qwen3.infer",),
        removable_capabilities=(),
    )
    part = ModelPart(
        part_id="qwen3.cpu.main",
        architecture="Qwen3",
        task_contract=TaskContract(
            task_id="qwen3.cpu.inference",
            capabilities=(Capability("qwen3.infer"),),
        ),
        role_contract=role,
    )
    registry = HardwareAssignmentRegistry()
    assignment = registry.assign(
        model_id="qwen3",
        part_id=part.part_id,
        role_contract=role,
        native_architecture="Qwen3",
    )
    hardware = CorelessCPUHardware(
        part=part,
        assignment=assignment,
        adapter=adapter,
        available_capabilities=("qwen3.infer",),
    )
    bridge = CorelessCPUBridge(hardware)

    response = bridge.handle(
        HardwareRequest(
            source="coreless.cpu.scheduler",
            target=part.part_id,
            operation="cpu.infer",
            payload=(0, 1),
            required_capabilities=("qwen3.infer",),
        )
    )

    assert response.source == "qwen3.cpu.main"
    assert response.target == "coreless.cpu.scheduler"
    assert response.operation == "cpu.infer"
    assert response.result.shape == (2, config.vocab_size)
    assert len(response.result.data) == 2 * config.vocab_size
    assert all(value == value for value in response.result.data)  # no NaNs
    assert any(value != 0.0 for value in response.result.data)


def test_qwen3_cpu_role_rejects_wrong_target_before_execution():
    config, weights = _tiny_qwen3_weights()
    from machine_runtime import CorelessMachine
    machine = CorelessMachine(memory_size=4096)
    role = RoleContract(
        role=ComponentRole.CPU,
        mandatory_capabilities=("qwen3.infer",),
    )
    part = ModelPart(
        part_id="qwen3.cpu.main",
        architecture="Qwen3",
        task_contract=TaskContract(
            task_id="qwen3.cpu.inference",
            capabilities=(Capability("qwen3.infer"),),
        ),
        role_contract=role,
    )
    assignment = HardwareAssignmentRegistry().assign(
        model_id="qwen3",
        part_id=part.part_id,
        role_contract=role,
        native_architecture="Qwen3",
    )
    bridge = CorelessCPUBridge(
        CorelessCPUHardware(
            part=part,
            assignment=assignment,
            adapter=Qwen3CPUAdapter(config, weights, tensor_runtime=machine.tensor_runtime),
            available_capabilities=("qwen3.infer",),
        )
    )

    import pytest

    with pytest.raises(ValueError, match="target does not match CPU hardware"):
        bridge.handle(
            HardwareRequest(
                source="coreless.cpu.scheduler",
                target="wrong.cpu.part",
                operation="cpu.infer",
                payload=(0,),
            )
        )


def test_qwen3_cpu_bridge_rejects_unassigned_capability():
    config, weights = _tiny_qwen3_weights()
    from machine_runtime import CorelessMachine
    machine = CorelessMachine(memory_size=4096)
    role = RoleContract(
        role=ComponentRole.CPU,
        mandatory_capabilities=("qwen3.infer",),
    )
    part = ModelPart(
        part_id="qwen3.cpu.main",
        architecture="Qwen3",
        task_contract=TaskContract(
            task_id="qwen3.cpu.inference",
            capabilities=(Capability("qwen3.infer"),),
        ),
        role_contract=role,
    )
    assignment = HardwareAssignmentRegistry().assign(
        model_id="qwen3",
        part_id=part.part_id,
        role_contract=role,
        native_architecture="Qwen3",
    )
    bridge = CorelessCPUBridge(
        CorelessCPUHardware(
            part=part,
            assignment=assignment,
            adapter=Qwen3CPUAdapter(config, weights, tensor_runtime=machine.tensor_runtime),
            available_capabilities=("qwen3.infer",),
        )
    )

    import pytest

    with pytest.raises(PermissionError, match="does not expose requested capabilities"):
        bridge.handle(
            HardwareRequest(
                source="coreless.cpu.scheduler",
                target=part.part_id,
                operation="cpu.infer",
                payload=(0,),
                required_capabilities=("filesystem.write",),
            )
        )


def test_qwen3_executes_through_machine_ai_chipset_scheduler_and_cpu_tensor_runtime():
    from ai.compute_fabric import ComputeWork
    from ai.interfaces import AIRequest
    from ai.registry import AICoreRegistry
    from machine_runtime import CorelessMachine

    config, weights = _tiny_qwen3_weights()
    machine = CorelessMachine(memory_size=4096)
    adapter = Qwen3CPUAdapter(
        config,
        weights,
        tensor_runtime=machine.tensor_runtime,
    )
    registry = AICoreRegistry()
    registry.register(adapter)
    assert machine.attach_ai_registry(registry) == ("qwen3",)

    request = AIRequest(
        request_id="qwen3-cpu-proof-1",
        prompt="",
        context={"token_ids": [0, 1]},
    )
    work = ComputeWork(
        work_id="qwen3-cpu-work-1",
        operation="ai.infer",
        request=request,
        model_id="qwen3",
    )
    result = machine.ai_chipset.dispatch(work)

    assert result.work_id == "qwen3-cpu-work-1"
    assert result.operation == "ai.infer"
    assert result.model_id == "qwen3"
    assert result.result.request_id == "qwen3-cpu-proof-1"
    assert result.result.model_id == "qwen3"
    assert result.result.metadata["runtime"] == "native-qwen3"
    assert result.result.metadata["logit_shape"] == (2, config.vocab_size)
    assert result.result.metadata["input_tokens"] == 2
    assert machine.ai_chipset.snapshot()["last_resource_id"] == "ai:qwen3"
    assert machine.ai_chipset.snapshot()["completed_work"] == 1
    assert adapter.tensor_runtime is machine.tensor_runtime
    assert adapter.tensor_runtime.cpu is machine.cpu
    assert machine.motherboard.ai_chipset_status()["busy"] is False
