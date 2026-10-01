from component_requirements import (
    CURRENT_COMPUTER_ENVELOPE,
    make_profile,
)


def test_reference_envelope_covers_compute_and_external_io():
    for capability in (
        "scalar_compute",
        "matrix_compute",
        "tensor_compute",
        "nvme",
        "pcie",
        "ethernet",
        "wifi",
        "display_output",
        "usb4_class_io",
        "capability_security",
        "error_correction",
    ):
        assert CURRENT_COMPUTER_ENVELOPE.contains(capability)


def test_specialization_selects_a_subset():
    profile = make_profile(
        "task.ai-device",
        required=("tensor_compute", "matrix_compute", "high_speed_io"),
        optional=("gpu_compute", "network_acceleration"),
    )
    assert "tensor_compute" in profile.required
    assert "gpu_compute" in profile.optional


def test_unknown_requirement_is_rejected():
    try:
        make_profile("task.invalid", required=("invented_device_feature",))
    except ValueError as exc:
        assert "invented_device_feature" in str(exc)
    else:
        raise AssertionError("unknown capability should be rejected")
