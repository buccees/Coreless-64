from ai.audit import AuditLog
from ai.interfaces import AIProposal
from ai.management import ManagementPlane
from ai.policy import DeterministicPolicy
from ai.resource_control import CorelessResourceController
from ai.telemetry import TelemetryProvider


class Compute:
    def submit(self, operation, payload):
        return "job-1"


def test_management_plane_connects_telemetry_control_and_audit():
    policy = DeterministicPolicy()
    controller = CorelessResourceController(policy, compute=Compute())
    controller.register_defaults()
    controller.grant("compute.submit", "cap-compute")
    telemetry = TelemetryProvider()
    telemetry.publish(cpu={"busy": 0.5})
    audit = AuditLog()
    plane = ManagementPlane(controller, telemetry=telemetry, audit=audit)

    proposal = AIProposal(
        "p1", "qwen3", "compute.submit",
        {"operation": "step", "payload": {}},
        capability="cap-compute",
    )
    result = plane.execute(proposal)

    assert result.allowed is True
    assert result.result == {"job_id": "job-1"}
    assert plane.snapshot().cpu["busy"] == 0.5
    assert audit.records()[0].operation == "compute.submit"


def test_management_plane_audits_denied_action():
    policy = DeterministicPolicy()
    controller = CorelessResourceController(policy, compute=Compute())
    controller.register_defaults()
    plane = ManagementPlane(controller)

    proposal = AIProposal("p2", "qwen3", "compute.submit", {"operation": "step", "payload": {}})
    try:
        plane.execute(proposal)
    except PermissionError:
        pass
    else:
        raise AssertionError("unauthorized action must fail")
    assert plane.audit.records()[0].outcome == "denied_or_failed"
