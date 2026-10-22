"""Deterministic temporal grouping of normalized VIGIL sensor evidence.

Grouping indicates time proximity only. It does not perform spatial fusion,
infer object identity, or convert Wi-Fi CSI/context into a position fix.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .sensor_event import SensorEventRecord, SensorEventStatus


def group_temporal_evidence(
    events: Iterable[SensorEventRecord],
    *,
    alignment_by_id: Mapping[str, Mapping[str, Any]] | None = None,
    window_ns: int = 50_000_000,
) -> tuple[dict[str, Any], ...]:
    """Group events within a fixed window anchored at the earliest event.

    A chain of individually close events cannot stretch a group beyond window_ns.
    Provenance and uncertainty remain attached to each member; no location is synthesized.
    """
    if isinstance(window_ns, bool) or not isinstance(window_ns, int) or window_ns < 0:
        raise ValueError("window_ns must be a non-negative integer")
    alignment_by_id = alignment_by_id or {}
    normalized = []
    seen = set()
    for event in events:
        if not isinstance(event, SensorEventRecord):
            raise TypeError("events must contain only SensorEventRecord values")
        if event.event_id in seen:
            raise ValueError(f"duplicate event_id: {event.event_id}")
        seen.add(event.event_id)
        alignment = alignment_by_id.get(event.event_id, {})
        aligned = alignment.get("aligned_timestamp_ns", event.timestamp_ns)
        if isinstance(aligned, bool) or not isinstance(aligned, int) or aligned < 0:
            raise ValueError(f"invalid aligned timestamp for event {event.event_id}")
        normalized.append((aligned, event, alignment))
    normalized.sort(key=lambda item: (item[0], item[1].event_id))

    groups = []
    members = []
    anchor = None

    def flush():
        if not members:
            return
        group_events = [entry[1] for entry in members]
        context_ids = [
            event.event_id for event in group_events
            if event.status == SensorEventStatus.CONTEXT
            or event.modality.lower() in {"wifi_csi", "wifi_telemetry"}
        ]
        groups.append({
            "start_timestamp_ns": members[0][0],
            "end_timestamp_ns": members[-1][0],
            "window_ns": window_ns,
            "event_ids": [event.event_id for event in group_events],
            "modalities": sorted({event.modality for event in group_events}),
            "context_event_ids": context_ids,
            "members": [
                {
                    "event_id": event.event_id,
                    "sensor_id": event.sensor_id,
                    "timestamp_ns": event.timestamp_ns,
                    "aligned_timestamp_ns": aligned,
                    "modality": event.modality,
                    "event_kind": event.event_kind,
                    "status": event.status.value,
                    "reason": event.reason,
                    "confidence": event.confidence,
                    "evidence_score": event.evidence_score,
                    "uncertainty_m": event.uncertainty_m,
                    "calibration_status": event.calibration_status,
                    "model_id": event.model_id,
                    "model_revision": event.model_revision,
                    "frame_id": event.frame_id,
                    "alignment": dict(alignment),
                }
                for aligned, event, alignment in members
            ],
            "spatial_position_inferred": False,
        })
        members.clear()

    for item in normalized:
        if anchor is None or item[0] - anchor <= window_ns:
            if anchor is None:
                anchor = item[0]
            members.append(item)
        else:
            flush()
            anchor = item[0]
            members.append(item)
    flush()
    return tuple(groups)
