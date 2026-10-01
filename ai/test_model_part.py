from model_part import (
    Capability,
    ModelPart,
    PartState,
    StaticAdaptiveSpecializer,
    TaskContract,
)


def test_candidate_must_validate_before_replacement():
    task = TaskContract(
        task_id="task.demo",
        capabilities=(Capability("compute.demo"),),
    )
    active = ModelPart("part.base", "deepseek-v3", task, state=PartState.ACTIVE)
    specializer = StaticAdaptiveSpecializer()

    candidate = specializer.propose(
        active, task, reason="observed workload", candidate_id="part.adapted"
    )
    assert candidate.state is PartState.CANDIDATE
    assert specializer.validate(candidate, [True, True])
    record = specializer.commit_replacement(active, candidate)

    assert record.validation_passed
    assert active.state is PartState.RETIRED
    assert candidate.state is PartState.ACTIVE


def test_failed_adaptation_does_not_replace_active_part():
    task = TaskContract("task.demo", (Capability("compute.demo"),))
    active = ModelPart("part.base", "qwen", task, state=PartState.ACTIVE)
    specializer = StaticAdaptiveSpecializer()

    candidate = specializer.propose(
        active, task, reason="new workload", candidate_id="part.bad"
    )
    assert not specializer.validate(candidate, [True, False])
    assert candidate.state is PartState.RETIRED
    assert active.state is PartState.ACTIVE


def test_capability_contract_is_explicit():
    task = TaskContract(
        "task.vision",
        (Capability("vision.encode", inputs=("image",), outputs=("embedding",)),),
    )
    part = ModelPart("part.vision", "gemma", task)

    assert part.satisfies("task.vision", "vision.encode")
    assert not part.satisfies("task.text", "vision.encode")


def test_role_contract_preserves_retained_optional_capabilities():
    role = RoleContract(
        role=ComponentRole.GPU,
        mandatory_capabilities=("matrix_compute", "graphics"),
        retained_optional_capabilities=("driver_compatibility",),
        removable_capabilities=("unrelated_capability",),
    )
    part = ModelPart(
        part_id="gpu-1",
        architecture="native-gpu-model",
        task_contract=TaskContract("graphics", (Capability("graphics"),)),
        role_contract=role,
        retained_parameters=("driver_compatibility",),
    )
    assert not part.can_remove_capability("driver_compatibility")
    assert part.can_remove_capability("unrelated_capability")


def test_communication_role_cannot_drop_user_communication():
    role = RoleContract(
        role=ComponentRole.COMMUNICATION,
        mandatory_capabilities=("language", "dialogue"),
        user_communication=True,
    )
    part = ModelPart(
        part_id="comm-1",
        architecture="native-language-model",
        task_contract=TaskContract("user-communication", (Capability("dialogue"),)),
        role_contract=role,
    )
    assert part.role_contract.user_communication


def test_hardware_assignment_preserves_native_architecture_and_role():
    role = RoleContract(
        role=ComponentRole.CPU,
        mandatory_capabilities=("scalar_compute",),
        retained_optional_capabilities=("cryptographic_compute",),
    )
    registry = HardwareAssignmentRegistry()
    assignment = registry.assign(
        "trained-cpu-model",
        "cpu-0",
        role,
        native_architecture="native-model-architecture",
    )
    assignment.validate(("scalar_compute", "cryptographic_compute"))
    assert assignment.native_architecture == "native-model-architecture"
    assert registry.get(ComponentRole.CPU).model_id == "trained-cpu-model"


def test_hardware_assignment_rejects_missing_role_capability():
    role = RoleContract(
        role=ComponentRole.GPU,
        mandatory_capabilities=("matrix_compute",),
    )
    assignment = HardwareAssignment(
        model_id="gpu-model",
        part_id="gpu-0",
        role_contract=role,
        required_capabilities=("matrix_compute",),
        retained_optional_capabilities=(),
        native_architecture="native-gpu",
    )
    try:
        assignment.validate(())
    except ValueError as exc:
        assert "matrix_compute" in str(exc)
    else:
        raise AssertionError("missing hardware capability was accepted")
