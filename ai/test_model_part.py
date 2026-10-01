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
