"""Adapters from existing VIGIL telemetry pipelines to normalized events.

CSI is recorded as contextual motion evidence only; it is not a position fix.
Adapters preserve supplied measurements and do not synthesize detections.
"""
from __future__ import annotations

from .csi_pipeline import CsiPipelineResult
from .sensor_event import SensorEventRecord, SensorEventStatus
from .telemetry_store import TelemetryEvent


def csi_result_to_sensor_event(result: CsiPipelineResult) -> SensorEventRecord:
    """Normalize a CSI pipeline result without implying object localization."""
    if not isinstance(result, CsiPipelineResult):
        raise TypeError("result must be a CsiPipelineResult")
    row_id = result.telemetry_row_id
    return SensorEventRecord(
        event_id=f"csi:{result.sensor_id}:{result.timestamp_ns}:{row_id}",
        sensor_id=result.sensor_id,
        timestamp_ns=result.timestamp_ns,
        modality="wifi_csi",
        event_kind="csi_motion_evidence",
        status=SensorEventStatus.CONTEXT,
        reason="CSI motion evidence only; not a position fix or object identity.",
        sequence=row_id if row_id >= 0 else None,
        evidence_score=result.motion.smoothed_evidence,
        calibration_status="environment_calibration_required",
        model_id="csi-motion-heuristic",
        model_revision="unvalidated",
    )


def telemetry_to_sensor_event(event: TelemetryEvent, *, sequence: int | None = None) -> SensorEventRecord:
    """Normalize one persisted telemetry input while retaining its evidence semantics."""
    if not isinstance(event, TelemetryEvent):
        raise TypeError("event must be a TelemetryEvent")
    is_csi = "csi" in event.event_kind.lower()
    modality = "wifi_csi" if is_csi else "wifi_telemetry"
    status = SensorEventStatus.CONTEXT
    reason = (
        "CSI-derived motion context only; no position or object identity inferred."
        if is_csi else
        "Network telemetry metadata only; no spatial detection inferred."
    )
    return SensorEventRecord(
        event_id=f"telemetry:{event.sensor_id}:{event.timestamp_ns}:{sequence if sequence is not None else 'na'}",
        sensor_id=event.sensor_id,
        timestamp_ns=event.timestamp_ns,
        modality=modality,
        event_kind=event.event_kind,
        status=status,
        reason=reason,
        sequence=sequence,
        signal_dbm=event.signal_dbm,
        evidence_score=event.motion_evidence,
        calibration_status="not_position_calibrated",
    )
