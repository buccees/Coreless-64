"""End-to-end CSI evidence pipeline for VIGIL's local telemetry store.

This pipeline turns aligned CSI vectors into filtered motion evidence and stores
metadata for diagnostics. It does not estimate object position or claim that
motion evidence alone identifies/tracks an object.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .rf_csi import CsiFeatures, MotionEvidenceFilter, MotionState, extract_csi_features
from .telemetry_store import TelemetryEvent, TelemetryStore


@dataclass(frozen=True)
class CsiPipelineResult:
    timestamp_ns: int
    sensor_id: str
    channel_mhz: int
    features: CsiFeatures
    motion: MotionState
    telemetry_row_id: int


class CsiTelemetryPipeline:
    """Process ordered CSI samples and persist their filtered evidence."""

    def __init__(
        self,
        *,
        sensor_id: str,
        channel_mhz: int,
        store: TelemetryStore,
        motion_filter: MotionEvidenceFilter | None = None,
    ) -> None:
        if not isinstance(sensor_id, str) or not sensor_id.strip():
            raise ValueError("sensor_id must be a non-empty string")
        if isinstance(channel_mhz, bool) or not isinstance(channel_mhz, int) or channel_mhz <= 0:
            raise ValueError("channel_mhz must be a positive integer")
        if not isinstance(store, TelemetryStore):
            raise TypeError("store must be a TelemetryStore")
        self.sensor_id = sensor_id
        self.channel_mhz = channel_mhz
        self.store = store
        self.motion_filter = motion_filter or MotionEvidenceFilter()
        self._last_timestamp_ns: int | None = None

    def process(
        self,
        *,
        timestamp_ns: int,
        baseline: Sequence[complex],
        current: Sequence[complex],
        packet_length: int = 0,
        signal_dbm: float | None = None,
    ) -> CsiPipelineResult:
        """Process one CSI sample; timestamps must be strictly increasing."""
        if isinstance(timestamp_ns, bool) or not isinstance(timestamp_ns, int) or timestamp_ns < 0:
            raise ValueError("timestamp_ns must be a non-negative integer")
        if self._last_timestamp_ns is not None and timestamp_ns <= self._last_timestamp_ns:
            raise ValueError("CSI timestamps must be strictly increasing")
        if isinstance(packet_length, bool) or not isinstance(packet_length, int) or packet_length < 0:
            raise ValueError("packet_length must be a non-negative integer")
        if signal_dbm is not None and not isfinite(signal_dbm):
            raise ValueError("signal_dbm must be finite when provided")

        features = extract_csi_features(baseline, current)
        motion = self.motion_filter.update(features.motion_evidence)
        row_id = self.store.record(TelemetryEvent(
            timestamp_ns=timestamp_ns,
            sensor_id=self.sensor_id,
            event_kind="csi_motion_evidence",
            protocol="802.11",
            packet_length=packet_length,
            channel_mhz=self.channel_mhz,
            signal_dbm=signal_dbm,
            motion_evidence=motion.smoothed_evidence,
            motion_active=motion.active,
        ))
        self._last_timestamp_ns = timestamp_ns
        return CsiPipelineResult(
            timestamp_ns, self.sensor_id, self.channel_mhz, features, motion, row_id
        )
