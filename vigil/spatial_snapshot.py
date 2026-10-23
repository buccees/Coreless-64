"""Versioned JSON contract for the live VIGIL spatial operator overlay.

The contract is presentation-only: it serializes the active model, last pose,
feature markers, track trails, and explicit region checks. It never creates
sensor data or turns stale/unknown evidence into a current position.
"""
from __future__ import annotations

from typing import Any

from .blueprint_view import build_blueprint_view
from .workspace import SpatialWorkspace


SPATIAL_PROTOCOL_VERSION = 1


def _point(point) -> list[float]:
    return [float(value) for value in point]


def build_spatial_snapshot(
    workspace: SpatialWorkspace,
    *,
    now_ns: int,
    max_age_ns: int = 2_000_000_000,
) -> dict[str, Any]:
    """Return a JSON-ready, precision-safe spatial snapshot for authenticated UI."""
    if not isinstance(workspace, SpatialWorkspace):
        raise TypeError("workspace must be a SpatialWorkspace")
    if isinstance(now_ns, bool) or not isinstance(now_ns, int) or now_ns < 0:
        raise ValueError("now_ns must be a non-negative integer")
    if isinstance(max_age_ns, bool) or not isinstance(max_age_ns, int) or max_age_ns < 0:
        raise ValueError("max_age_ns must be a non-negative integer")

    snapshot = workspace.refresh(now_ns=now_ns, max_age_ns=max_age_ns)
    model = snapshot.model
    poll_status_by_id = {
        item.provider_id: item for item in workspace.sensor_poll_statuses
    }
    base: dict[str, Any] = {
        "protocol_version": SPATIAL_PROTOCOL_VERSION,
        "generated_at_ns": str(now_ns),
        "available": model is not None,
        "status": "ready" if model is not None else "no_blueprint",
        "model": None,
        "pose": None,
        "spatial_query": None,
        "features": [],
        "objects": [],
        "regions": [],
        "sensor_providers": [{
            "provider_id": provider_id,
            "accepted": poll_status_by_id[provider_id].accepted if provider_id in poll_status_by_id else 0,
            "state": poll_status_by_id[provider_id].state if provider_id in poll_status_by_id else "UNPOLLED",
            "error": poll_status_by_id[provider_id].error if provider_id in poll_status_by_id else None,
        } for provider_id in workspace.sensor_provider_ids],
    }
    if model is None:
        return base

    view = build_blueprint_view(
        model, snapshot.pose, selected_level=snapshot.selected_level,
        object_tracks=snapshot.object_tracks,
    )
    # The renderer projection intentionally stays compact. Preserve the richer
    # evidence-quality metadata from the authoritative tracks in the API so an
    # operator can tell *why* a location is trusted, not just where it appears.
    tracks_by_identity = {
        (track.object_id, track.association_id): track
        for track in snapshot.object_tracks
    }
    base.update({
        "model": {
            "model_id": model.model_id,
            "revision": model.revision,
            "frame_id": model.frame_id,
            "source_sha256": model.source_sha256,
            "selected_level": snapshot.selected_level,
            "bounds_m": [
                {"min": bound.minimum, "max": bound.maximum}
                for bound in view.bounds_m
            ],
        },
        "pose": None if snapshot.pose is None else {
            "state": snapshot.pose.state.value,
            "presence_state": (
                "UNKNOWN" if snapshot.pose.observation_timestamp_ns is None else
                "TIME_UNCERTAIN" if snapshot.pose.observation_timestamp_ns > now_ns else
                "STALE" if now_ns - snapshot.pose.observation_timestamp_ns > max_age_ns else
                "CURRENT"
            ),
            "position_m": _point(snapshot.pose.position_m) if snapshot.pose.position_m is not None else None,
            "uncertainty_m": snapshot.pose.uncertainty_m,
            "observation_timestamp_ns": (
                str(snapshot.pose.observation_timestamp_ns)
                if snapshot.pose.observation_timestamp_ns is not None else None
            ),
            "age_ns": (
                str(now_ns - snapshot.pose.observation_timestamp_ns)
                if snapshot.pose.observation_timestamp_ns is not None else None
            ),
            "reason": snapshot.pose.reason,
            "provenance": list(snapshot.pose.provenance),
        },
        "features": [{
            "feature_id": feature.feature_id,
            "label": feature.label,
            "feature_type": feature.feature_type,
            "level": feature.level,
            "zone": feature.zone,
            "position_m": _point(feature.position_m),
        } for feature in view.features],
        "objects": [{
            "object_id": item.object_id,
            "association_id": item.association_id,
            "position_m": _point(item.position_m),
            "velocity_mps": _point(item.velocity_mps),
            "speed_mps": item.speed_mps,
            "last_seen_ns": str(item.last_seen_ns),
            "age_ns": str(max(0, now_ns - item.last_seen_ns)),
            "uncertainty_m": item.uncertainty_m,
            "sensor_ids": list(item.sensor_ids),
            "modalities": list(item.modalities),
            "provenance": list(item.provenance),
            "observation_count": tracks_by_identity[
                (item.object_id, item.association_id)
            ].observation_count,
            "independence_groups": list(tracks_by_identity[
                (item.object_id, item.association_id)
            ].independence_groups),
            "calibration_status": tracks_by_identity[
                (item.object_id, item.association_id)
            ].calibration_status,
            "calibration_ids": list(tracks_by_identity[
                (item.object_id, item.association_id)
            ].calibration_ids),
            "lineage_declared": tracks_by_identity[
                (item.object_id, item.association_id)
            ].lineage_declared,
            "conflict": item.conflict,
            "conflict_reasons": list(item.conflict_reasons),
            "presence_state": item.presence_state,
            "motion_state": item.motion_state,
            "visible_on_selected_level": item.visible_on_selected_level,
            "motion_trail_m": [{
                "timestamp_ns": str(timestamp),
                "position_m": _point(position),
            } for timestamp, position in item.motion_trail_m],
        } for item in view.objects],
    })
    if snapshot.spatial_query is not None:
        query = snapshot.spatial_query
        base["spatial_query"] = {
            "status": query.status.value,
            "position_m": _point(query.position_m) if query.position_m is not None else None,
            "nearest_feature_id": query.nearest_feature_id,
            "nearest_feature_label": query.nearest_feature_label,
            "nearest_feature_distance_m": query.nearest_feature_distance_m,
            "level": query.level,
            "zone": query.zone,
            "uncertainty_m": query.uncertainty_m,
            "reason": query.reason,
        }
    results = {result.region_id: result for result in snapshot.region_results}
    base["regions"] = [{
        "region_id": region.region_id,
        "label": region.label,
        "polygon_xy_m": [[float(x), float(y)] for x, y in region.polygon_xy_m],
        "min_z_m": region.min_z_m,
        "max_z_m": region.max_z_m,
        "level": region.level,
        "zone": region.zone,
        "status": results[region.region_id].status.value if region.region_id in results else "NO_FIX",
        "inside": results[region.region_id].inside if region.region_id in results else None,
        "reason": results[region.region_id].reason if region.region_id in results else "region has no current query result",
    } for region in workspace.spatial_regions
       if region.level is None or snapshot.selected_level is None or region.level == snapshot.selected_level]
    return base
