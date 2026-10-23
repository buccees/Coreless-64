"""Persistent SQLite registry for validated VIGIL models, regions, and raster calibrations.

The database stores normalized spatial metadata only; original drawings/images and
sensor payloads remain separate. Records are deterministic JSON with SHA-256
integrity checks, SQL-bound parameters, size limits, and immutable model/region
identities. Revisions must change when geometry changes.
"""
from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import asdict
from hashlib import sha256
import json
import sqlite3
from typing import Any

from .blueprint import BlueprintModel, ModelFeature, _validate_vector
from .object_tracking import ObjectObservation, ObjectTrack, TrackingModality
from .raster_calibration import RasterBlueprintCalibration
from .spatial_regions import SpatialRegion
from .sensor_mounts import SensorMountTransform


def _observation_payload(item: ObjectObservation) -> dict[str, Any]:
    return {
        "object_id": item.object_id, "sensor_id": item.sensor_id,
        "model_id": item.model_id, "model_revision": item.model_revision,
        "frame_id": item.frame_id, "timestamp_ns": item.timestamp_ns,
        "position_m": list(item.position_m), "uncertainty_m": item.uncertainty_m,
        "modality": item.modality.value, "provenance": item.provenance,
        "association_id": item.association_id,
        "independence_group": item.independence_group,
        "calibration_status": item.calibration_status,
        "calibration_ids": list(item.calibration_ids),
        "lineage_declared": item.lineage_declared,
    }


def _observation_from_payload(payload: dict[str, Any]) -> ObjectObservation:
    return ObjectObservation(
        object_id=payload["object_id"], sensor_id=payload["sensor_id"],
        model_id=payload["model_id"], model_revision=payload["model_revision"],
        frame_id=payload["frame_id"], timestamp_ns=payload["timestamp_ns"],
        position_m=tuple(payload["position_m"]), uncertainty_m=payload["uncertainty_m"],
        modality=TrackingModality(payload["modality"]), provenance=payload["provenance"],
        association_id=payload.get("association_id"),
        independence_group=payload.get("independence_group"),
        calibration_status=payload.get("calibration_status", "unverified"),
        calibration_ids=tuple(payload.get("calibration_ids", ())),
        lineage_declared=payload.get("lineage_declared", False),
    )


def _encode(payload: dict[str, Any], *, max_bytes: int) -> tuple[str, str]:
    try:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"spatial record is not valid finite JSON: {exc}") from exc
    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError(f"spatial record exceeds {max_bytes} byte limit")
    return encoded, sha256(encoded.encode("utf-8")).hexdigest()


def _decode(encoded: str, digest: str, *, max_bytes: int) -> dict[str, Any]:
    raw = encoded.encode("utf-8")
    if len(raw) > max_bytes:
        raise ValueError("stored spatial record exceeds configured size limit")
    if sha256(raw).hexdigest() != digest:
        raise ValueError("stored spatial record checksum mismatch")
    try:
        payload = json.loads(encoded, parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number is not allowed: {value}")
        ))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"stored spatial record is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("stored spatial record must be a JSON object")
    return payload


class SpatialRegistryStore:
    """SQLite persistence for blueprint revisions, explicit regions, and calibrations."""

    def __init__(self, database: str = ":memory:", *, max_record_bytes: int = 5_000_000) -> None:
        if not isinstance(database, str) or not database.strip():
            raise ValueError("database path must be a non-empty string")
        if isinstance(max_record_bytes, bool) or not isinstance(max_record_bytes, int) or max_record_bytes < 256:
            raise ValueError("max_record_bytes must be an integer of at least 256")
        self.max_record_bytes = max_record_bytes
        self._connection = sqlite3.connect(database)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS spatial_models (
                model_id TEXT NOT NULL,
                revision TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                PRIMARY KEY (model_id, revision)
            );
            CREATE TABLE IF NOT EXISTS spatial_regions (
                model_id TEXT NOT NULL,
                revision TEXT NOT NULL,
                region_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                PRIMARY KEY (model_id, revision, region_id)
            );
            CREATE TABLE IF NOT EXISTS spatial_source_assets (
                model_id TEXT NOT NULL,
                revision TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                asset_name TEXT NOT NULL,
                media_type TEXT NOT NULL,
                content BLOB NOT NULL,
                content_sha256 TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                metadata_sha256 TEXT NOT NULL,
                PRIMARY KEY (model_id, revision, asset_id)
            );
            CREATE INDEX IF NOT EXISTS idx_spatial_assets_model
                ON spatial_source_assets(model_id, revision, asset_id);
            CREATE TABLE IF NOT EXISTS raster_calibrations (
                calibration_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                revision TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sensor_mount_transforms (
                mount_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                revision TEXT NOT NULL,
                sensor_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sensor_mount_model
                ON sensor_mount_transforms(model_id, revision, sensor_id, mount_id);
            CREATE INDEX IF NOT EXISTS idx_raster_calibration_model
                ON raster_calibrations(model_id, revision, calibration_id);
            CREATE TABLE IF NOT EXISTS spatial_object_tracks (
                model_id TEXT NOT NULL,
                revision TEXT NOT NULL,
                tracking_key TEXT NOT NULL,
                last_seen_ns INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                PRIMARY KEY (model_id, revision, tracking_key)
            );
            CREATE INDEX IF NOT EXISTS idx_spatial_tracks_last_seen
                ON spatial_object_tracks(model_id, revision, last_seen_ns);
            CREATE TABLE IF NOT EXISTS expected_sensor_coverage (
                model_id TEXT NOT NULL,
                revision TEXT NOT NULL,
                sensor_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                PRIMARY KEY (model_id, revision, sensor_id)
            );
            CREATE TABLE IF NOT EXISTS sensor_lifecycle_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sensor_alert_acknowledgements (
                alert_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS spatial_store_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            );
        """)
        self._connection.commit()

    def save_model(self, model: BlueprintModel, *, activate: bool = False) -> BlueprintModel:
        if not isinstance(model, BlueprintModel):
            raise TypeError("model must be a validated BlueprintModel")
        payload = {
            "model_id": model.model_id, "revision": model.revision,
            "frame_id": model.frame_id, "source_units": model.source_units,
            "source_sha256": model.source_sha256,
            "features": [{
                "feature_id": item.feature_id, "label": item.label,
                "position_m": list(item.position_m), "feature_type": item.feature_type,
                "level": item.level, "zone": item.zone,
            } for item in model.features],
            "metadata": dict(model.metadata),
        }
        encoded, digest = _encode(payload, max_bytes=self.max_record_bytes)
        with self._connection:
            row = self._connection.execute(
                "SELECT payload_json, payload_sha256 FROM spatial_models WHERE model_id=? AND revision=?",
                (model.model_id, model.revision),
            ).fetchone()
            if row is not None and (row["payload_json"] != encoded or row["payload_sha256"] != digest):
                raise ValueError("model ID/revision is immutable; use a new revision for changed content")
            self._connection.execute(
                "INSERT OR IGNORE INTO spatial_models(model_id,revision,payload_json,payload_sha256) VALUES(?,?,?,?)",
                (model.model_id, model.revision, encoded, digest),
            )
            if activate:
                self._connection.execute(
                    "INSERT INTO spatial_store_settings(setting_key,setting_value) VALUES('active_model',?) "
                    "ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value",
                    (json.dumps([model.model_id, model.revision], separators=(",", ":")),),
                )
        return model

    def set_active_model(self, model_id: str, revision: str) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (model_id, revision)):
            raise ValueError("model_id and revision are required")
        with self._connection:
            exists = self._connection.execute(
                "SELECT 1 FROM spatial_models WHERE model_id=? AND revision=?",
                (model_id, revision),
            ).fetchone()
            if exists is None:
                raise KeyError(f"cannot activate an unregistered model revision: {model_id}/{revision}")
            self._connection.execute(
                "INSERT INTO spatial_store_settings(setting_key,setting_value) VALUES('active_model',?) "
                "ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value",
                (json.dumps([model_id, revision], separators=(",", ":")),),
            )

    @property
    def active_model_ref(self) -> tuple[str, str] | None:
        row = self._connection.execute(
            "SELECT setting_value FROM spatial_store_settings WHERE setting_key='active_model'"
        ).fetchone()
        if row is None:
            return None
        try:
            data = json.loads(row["setting_value"])
        except json.JSONDecodeError as exc:
            raise ValueError("active spatial model pointer is corrupt") from exc
        if (not isinstance(data, list) or len(data) != 2
                or not all(isinstance(value, str) and value for value in data)):
            raise ValueError("active spatial model pointer is invalid")
        return data[0], data[1]

    def load_model(self, model_id: str, revision: str) -> BlueprintModel | None:
        row = self._connection.execute(
            "SELECT payload_json,payload_sha256 FROM spatial_models WHERE model_id=? AND revision=?",
            (model_id, revision),
        ).fetchone()
        if row is None:
            return None
        payload = _decode(row["payload_json"], row["payload_sha256"], max_bytes=self.max_record_bytes)
        expected = ("model_id", "revision", "frame_id", "source_units", "source_sha256", "features", "metadata")
        if any(key not in payload for key in expected):
            raise ValueError("stored model is missing required fields")
        if payload["model_id"] != model_id or payload["revision"] != revision:
            raise ValueError("stored model key does not match its record")
        if not isinstance(payload["features"], list) or not isinstance(payload["metadata"], dict):
            raise ValueError("stored model geometry or metadata has invalid shape")
        features = tuple(ModelFeature(
            feature_id=item["feature_id"], label=item["label"],
            position_m=_validate_vector(item["position_m"], "stored feature position"),
            feature_type=item.get("feature_type", "anchor"),
            level=item.get("level"), zone=item.get("zone"),
        ) for item in payload["features"])
        return BlueprintModel(
            model_id=payload["model_id"], revision=payload["revision"],
            frame_id=payload["frame_id"], source_units=payload["source_units"],
            features=features, source_sha256=payload["source_sha256"],
            metadata=payload["metadata"],
        )

    def list_models(self) -> tuple[BlueprintModel, ...]:
        keys = self._connection.execute(
            "SELECT model_id,revision FROM spatial_models ORDER BY model_id,revision"
        ).fetchall()
        return tuple(model for key in keys if (
            model := self.load_model(key["model_id"], key["revision"])
        ) is not None)

    def save_source_asset(
        self, model_id: str, revision: str, asset_id: str, *,
        asset_name: str, media_type: str, content: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist an immutable original source asset tied to one model revision.

        The normalized model is kept separately. Original bytes are checksummed
        so a portable machine can carry the exact source manifest or drawing.
        """
        identity = (model_id, revision, asset_id, asset_name, media_type)
        if not all(isinstance(value, str) and value.strip() for value in identity):
            raise ValueError("model/revision/asset identity, name, and media type are required")
        if not isinstance(content, bytes):
            raise TypeError("source asset content must be bytes")
        if len(content) > self.max_record_bytes:
            raise ValueError(f"source asset exceeds {self.max_record_bytes} byte limit")
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise TypeError("source asset metadata must be a dictionary")
        encoded_metadata, metadata_digest = _encode(metadata, max_bytes=self.max_record_bytes)
        content_digest = sha256(content).hexdigest()
        with self._connection:
            model_exists = self._connection.execute(
                "SELECT 1 FROM spatial_models WHERE model_id=? AND revision=?",
                (model_id, revision),
            ).fetchone()
            if model_exists is None:
                raise KeyError(f"source asset model revision is not registered: {model_id}/{revision}")
            old = self._connection.execute(
                "SELECT asset_name,media_type,content,content_sha256,metadata_json,metadata_sha256 "
                "FROM spatial_source_assets WHERE model_id=? AND revision=? AND asset_id=?",
                (model_id, revision, asset_id),
            ).fetchone()
            if old is not None and (
                old["asset_name"] != asset_name or old["media_type"] != media_type
                or bytes(old["content"]) != content or old["content_sha256"] != content_digest
                or old["metadata_json"] != encoded_metadata
                or old["metadata_sha256"] != metadata_digest
            ):
                raise ValueError("source asset ID is immutable within a model revision")
            self._connection.execute(
                "INSERT OR IGNORE INTO spatial_source_assets"
                "(model_id,revision,asset_id,asset_name,media_type,content,content_sha256,metadata_json,metadata_sha256) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (model_id, revision, asset_id, asset_name, media_type, sqlite3.Binary(content),
                 content_digest, encoded_metadata, metadata_digest),
            )
        return {
            "model_id": model_id, "revision": revision, "asset_id": asset_id,
            "asset_name": asset_name, "media_type": media_type,
            "content": content, "content_sha256": content_digest, "metadata": metadata,
        }

    def load_source_asset(
        self, model_id: str, revision: str, asset_id: str,
    ) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT asset_name,media_type,content,content_sha256,metadata_json,metadata_sha256 "
            "FROM spatial_source_assets WHERE model_id=? AND revision=? AND asset_id=?",
            (model_id, revision, asset_id),
        ).fetchone()
        if row is None:
            return None
        content = bytes(row["content"])
        if len(content) > self.max_record_bytes:
            raise ValueError("stored source asset exceeds configured size limit")
        if sha256(content).hexdigest() != row["content_sha256"]:
            raise ValueError("stored source asset checksum mismatch")
        metadata = _decode(
            row["metadata_json"], row["metadata_sha256"], max_bytes=self.max_record_bytes,
        )
        return {
            "model_id": model_id, "revision": revision, "asset_id": asset_id,
            "asset_name": row["asset_name"], "media_type": row["media_type"],
            "content": content, "content_sha256": row["content_sha256"], "metadata": metadata,
        }

    def list_source_assets(self, model_id: str, revision: str) -> tuple[dict[str, Any], ...]:
        rows = self._connection.execute(
            "SELECT asset_id FROM spatial_source_assets WHERE model_id=? AND revision=? "
            "ORDER BY asset_id", (model_id, revision),
        ).fetchall()
        return tuple(
            asset for row in rows
            if (asset := self.load_source_asset(model_id, revision, row["asset_id"])) is not None
        )

    def save_region(self, region: SpatialRegion) -> SpatialRegion:
        if not isinstance(region, SpatialRegion):
            raise TypeError("region must be a SpatialRegion")
        payload = {
            "region_id": region.region_id, "label": region.label,
            "model_id": region.model_id, "model_revision": region.model_revision,
            "frame_id": region.frame_id, "polygon_xy_m": [list(point) for point in region.polygon_xy_m],
            "min_z_m": region.min_z_m, "max_z_m": region.max_z_m,
            "level": region.level, "zone": region.zone,
        }
        encoded, digest = _encode(payload, max_bytes=self.max_record_bytes)
        with self._connection:
            exists = self._connection.execute(
                "SELECT payload_json,payload_sha256 FROM spatial_regions "
                "WHERE model_id=? AND revision=? AND region_id=?",
                (region.model_id, region.model_revision, region.region_id),
            ).fetchone()
            if exists and (exists["payload_json"] != encoded or exists["payload_sha256"] != digest):
                raise ValueError("region ID is immutable within a model revision")
            self._connection.execute(
                "INSERT OR IGNORE INTO spatial_regions(model_id,revision,region_id,payload_json,payload_sha256) VALUES(?,?,?,?,?)",
                (region.model_id, region.model_revision, region.region_id, encoded, digest),
            )
        return region

    def load_regions(self, model_id: str, revision: str) -> tuple[SpatialRegion, ...]:
        rows = self._connection.execute(
            "SELECT region_id,payload_json,payload_sha256 FROM spatial_regions "
            "WHERE model_id=? AND revision=? ORDER BY region_id",
            (model_id, revision),
        ).fetchall()
        result = []
        for row in rows:
            payload = _decode(row["payload_json"], row["payload_sha256"], max_bytes=self.max_record_bytes)
            if payload.get("region_id") != row["region_id"]:
                raise ValueError("stored region key does not match its record")
            result.append(SpatialRegion(
                region_id=payload["region_id"], label=payload["label"],
                model_id=payload["model_id"], model_revision=payload["model_revision"],
                frame_id=payload["frame_id"],
                polygon_xy_m=tuple(tuple(point) for point in payload["polygon_xy_m"]),
                min_z_m=payload["min_z_m"], max_z_m=payload["max_z_m"],
                level=payload.get("level"), zone=payload.get("zone"),
            ))
        return tuple(result)

    def delete_region(self, model_id: str, revision: str, region_id: str) -> bool:
        with self._connection:
            cursor = self._connection.execute(
                "DELETE FROM spatial_regions WHERE model_id=? AND revision=? AND region_id=?",
                (model_id, revision, region_id),
            )
        return cursor.rowcount > 0

    def save_expected_sensor(self, model_id: str, revision: str, sensor_id: str, *, provider_id: str, region_ids: tuple[str, ...], max_age_ns: int) -> dict[str, Any]:
        """Persist an explicit expected-sensor reporting contract for a model revision."""
        if not all(isinstance(value, str) and value.strip() for value in (model_id, revision, sensor_id, provider_id)):
            raise ValueError("model, revision, sensor, and provider IDs must not be empty")
        if isinstance(max_age_ns, bool) or not isinstance(max_age_ns, int) or max_age_ns < 0:
            raise ValueError("max_age_ns must be a non-negative integer")
        normalized = tuple(sorted(set(region_ids)))
        if not normalized or any(not isinstance(value, str) or not value.strip() for value in normalized):
            raise ValueError("region_ids must contain non-empty region IDs")
        if self.load_model(model_id, revision) is None:
            raise KeyError(f"expected sensor model revision is not registered: {model_id}/{revision}")
        known = {region.region_id for region in self.load_regions(model_id, revision)}
        if set(normalized) - known:
            raise KeyError("expected sensor references an unknown region")
        payload = {"model_id": model_id, "revision": revision, "sensor_id": sensor_id, "provider_id": provider_id, "region_ids": list(normalized), "max_age_ns": max_age_ns}
        encoded, digest = _encode(payload, max_bytes=self.max_record_bytes)
        with self._connection:
            old = self._connection.execute("SELECT payload_json,payload_sha256 FROM expected_sensor_coverage WHERE model_id=? AND revision=? AND sensor_id=?", (model_id, revision, sensor_id)).fetchone()
            if old and (old["payload_json"] != encoded or old["payload_sha256"] != digest):
                raise ValueError("expected sensor configuration already exists; remove it before changing")
            self._connection.execute("INSERT OR IGNORE INTO expected_sensor_coverage(model_id,revision,sensor_id,payload_json,payload_sha256) VALUES(?,?,?,?,?)", (model_id, revision, sensor_id, encoded, digest))
        return payload

    def load_expected_sensors(self, model_id: str, revision: str) -> tuple[dict[str, Any], ...]:
        rows = self._connection.execute("SELECT sensor_id,payload_json,payload_sha256 FROM expected_sensor_coverage WHERE model_id=? AND revision=? ORDER BY sensor_id", (model_id, revision)).fetchall()
        result = []
        for row in rows:
            payload = _decode(row["payload_json"], row["payload_sha256"], max_bytes=self.max_record_bytes)
            if payload.get("sensor_id") != row["sensor_id"] or payload.get("model_id") != model_id or payload.get("revision") != revision:
                raise ValueError("stored expected sensor key does not match its record")
            result.append(payload)
        return tuple(result)

    def delete_expected_sensor(self, model_id: str, revision: str, sensor_id: str) -> bool:
        with self._connection:
            cursor = self._connection.execute("DELETE FROM expected_sensor_coverage WHERE model_id=? AND revision=? AND sensor_id=?", (model_id, revision, sensor_id))
        return cursor.rowcount > 0

    def save_calibration(
        self, calibration_id: str, calibration: RasterBlueprintCalibration
    ) -> str:
        if not isinstance(calibration_id, str) or not calibration_id.strip():
            raise ValueError("calibration_id must be a non-empty string")
        if not isinstance(calibration, RasterBlueprintCalibration):
            raise TypeError("calibration must be a RasterBlueprintCalibration")
        payload = {
            "model_id": calibration.model_id, "model_revision": calibration.model_revision,
            "frame_id": calibration.frame_id, "level_id": calibration.level_id,
            "elevation_m": calibration.elevation_m,
            "x_coefficients": list(calibration.x_coefficients),
            "y_coefficients": list(calibration.y_coefficients),
            "control_point_count": calibration.control_point_count,
            "rms_residual_m": calibration.rms_residual_m,
            "control_labels": list(calibration.control_labels),
        }
        encoded, digest = _encode(payload, max_bytes=self.max_record_bytes)
        with self._connection:
            old = self._connection.execute(
                "SELECT payload_json,payload_sha256 FROM raster_calibrations WHERE calibration_id=?",
                (calibration_id,),
            ).fetchone()
            if old and (old["payload_json"] != encoded or old["payload_sha256"] != digest):
                raise ValueError("calibration ID is immutable; use a new ID for recalibration")
            self._connection.execute(
                "INSERT OR IGNORE INTO raster_calibrations(calibration_id,model_id,revision,payload_json,payload_sha256) VALUES(?,?,?,?,?)",
                (calibration_id, calibration.model_id, calibration.model_revision, encoded, digest),
            )
        return calibration_id

    def load_calibration(self, calibration_id: str) -> RasterBlueprintCalibration | None:
        row = self._connection.execute(
            "SELECT payload_json,payload_sha256 FROM raster_calibrations WHERE calibration_id=?",
            (calibration_id,),
        ).fetchone()
        if row is None:
            return None
        payload = _decode(row["payload_json"], row["payload_sha256"], max_bytes=self.max_record_bytes)
        return RasterBlueprintCalibration(
            model_id=payload["model_id"], model_revision=payload["model_revision"],
            frame_id=payload["frame_id"], level_id=payload["level_id"],
            elevation_m=payload["elevation_m"],
            x_coefficients=tuple(payload["x_coefficients"]),
            y_coefficients=tuple(payload["y_coefficients"]),
            control_point_count=payload["control_point_count"],
            rms_residual_m=payload["rms_residual_m"],
            control_labels=tuple(payload["control_labels"]),
        )

    @staticmethod
    def _track_payload(track: ObjectTrack) -> dict[str, Any]:
        return {
            "object_id": track.object_id,
            "model_id": track.model_id,
            "model_revision": track.model_revision,
            "frame_id": track.frame_id,
            "position_m": list(track.position_m),
            "velocity_mps": list(track.velocity_mps),
            "uncertainty_m": track.uncertainty_m,
            "last_seen_ns": track.last_seen_ns,
            "sensor_ids": list(track.sensor_ids),
            "modalities": list(track.modalities),
            "observation_count": track.observation_count,
            "association_id": track.association_id,
            "provenance": list(track.provenance),
            "conflict": track.conflict,
            "conflict_reasons": list(track.conflict_reasons),
            "conflicting_sensor_ids": list(track.conflicting_sensor_ids),
            "independence_groups": list(track.independence_groups),
            "position_history_m": [
                [timestamp, list(position)]
                for timestamp, position in track.position_history_m
            ],
            "position_history_sensor_ids": [
                [timestamp, list(sensor_ids)]
                for timestamp, sensor_ids in track.position_history_sensor_ids
            ],
            "calibration_status": track.calibration_status,
            "calibration_ids": list(track.calibration_ids),
            "lineage_declared": track.lineage_declared,
            "presence_state": track.presence_state,
            "raw_observations": [_observation_payload(item) for item in track.raw_observations],
        }

    def save_sensor_mount(self, mount: SensorMountTransform) -> str:
        """Persist an immutable sensor-local-to-model transform."""
        if not isinstance(mount, SensorMountTransform):
            raise TypeError("mount must be a SensorMountTransform")
        payload = {
            "mount_id": mount.mount_id, "sensor_id": mount.sensor_id,
            "model_id": mount.model_id, "model_revision": mount.model_revision,
            "frame_id": mount.frame_id, "source_frame_id": mount.source_frame_id,
            "translation_m": list(mount.translation_m),
            "rotation_matrix": list(mount.rotation_matrix), "verified": mount.verified,
        }
        encoded, digest = _encode(payload, max_bytes=self.max_record_bytes)
        with self._connection:
            model_exists = self._connection.execute(
                "SELECT 1 FROM spatial_models WHERE model_id=? AND revision=?",
                (mount.model_id, mount.model_revision),
            ).fetchone()
            if model_exists is None:
                raise KeyError(f"sensor mount model revision is not registered: {mount.model_id}/{mount.model_revision}")
            old = self._connection.execute(
                "SELECT payload_json,payload_sha256 FROM sensor_mount_transforms WHERE mount_id=?",
                (mount.mount_id,),
            ).fetchone()
            if old and (old["payload_json"] != encoded or old["payload_sha256"] != digest):
                raise ValueError("sensor mount ID is immutable; use a new ID after recalibration")
            self._connection.execute(
                "INSERT OR IGNORE INTO sensor_mount_transforms"
                "(mount_id,model_id,revision,sensor_id,payload_json,payload_sha256) VALUES(?,?,?,?,?,?)",
                (mount.mount_id, mount.model_id, mount.model_revision, mount.sensor_id, encoded, digest),
            )
        return mount.mount_id

    def load_sensor_mount(self, mount_id: str) -> SensorMountTransform | None:
        row = self._connection.execute(
            "SELECT payload_json,payload_sha256 FROM sensor_mount_transforms WHERE mount_id=?",
            (mount_id,),
        ).fetchone()
        if row is None:
            return None
        payload = _decode(row["payload_json"], row["payload_sha256"], max_bytes=self.max_record_bytes)
        return SensorMountTransform(
            mount_id=payload["mount_id"], sensor_id=payload["sensor_id"],
            model_id=payload["model_id"], model_revision=payload["model_revision"],
            frame_id=payload["frame_id"], source_frame_id=payload["source_frame_id"],
            translation_m=tuple(payload["translation_m"]),
            rotation_matrix=tuple(payload["rotation_matrix"]), verified=payload["verified"],
        )

    def list_sensor_mounts(self, model_id: str, revision: str) -> tuple[SensorMountTransform, ...]:
        rows = self._connection.execute(
            "SELECT mount_id FROM sensor_mount_transforms WHERE model_id=? AND revision=? ORDER BY mount_id",
            (model_id, revision),
        ).fetchall()
        return tuple(
            mount for row in rows
            if (mount := self.load_sensor_mount(row["mount_id"])) is not None
        )

    @staticmethod
    def _track_from_payload(payload: dict[str, Any]) -> ObjectTrack:
        return ObjectTrack(
            object_id=payload["object_id"], model_id=payload["model_id"],
            model_revision=payload["model_revision"], frame_id=payload["frame_id"],
            position_m=tuple(payload["position_m"]), velocity_mps=tuple(payload["velocity_mps"]),
            uncertainty_m=payload["uncertainty_m"], last_seen_ns=payload["last_seen_ns"],
            sensor_ids=tuple(payload["sensor_ids"]), modalities=tuple(payload["modalities"]),
            observation_count=payload["observation_count"], association_id=payload.get("association_id"),
            provenance=tuple(payload.get("provenance", ())), conflict=payload.get("conflict", False),
            conflict_reasons=tuple(payload.get("conflict_reasons", ())),
            conflicting_sensor_ids=tuple(payload.get("conflicting_sensor_ids", ())),
            independence_groups=tuple(payload.get("independence_groups", ())),
            position_history_m=tuple((entry[0], tuple(entry[1])) for entry in payload.get("position_history_m", ())),
            position_history_sensor_ids=tuple((entry[0], tuple(entry[1])) for entry in payload.get("position_history_sensor_ids", ())),
            calibration_status=payload.get("calibration_status", "unverified"),
            calibration_ids=tuple(payload.get("calibration_ids", ())),
            lineage_declared=payload.get("lineage_declared", False),
            presence_state=payload.get("presence_state", "TRACKING"),
            raw_observations=tuple(_observation_from_payload(item) for item in payload.get("raw_observations", ())),
        )

    def save_object_tracks(
        self, model: BlueprintModel, tracks: tuple[ObjectTrack, ...] | list[ObjectTrack]
    ) -> int:
        """Atomically replace the persisted last-known track set for one model revision."""
        if not isinstance(model, BlueprintModel):
            raise TypeError("model must be a validated BlueprintModel")
        rows = []
        seen: set[str] = set()
        for track in tracks:
            if not isinstance(track, ObjectTrack):
                raise TypeError("tracks must contain ObjectTrack values")
            if (track.model_id, track.model_revision, track.frame_id) != (
                model.model_id, model.revision, model.frame_id
            ):
                raise ValueError("track must match model/revision/frame")
            tracking_key = (
                f"association:{track.association_id}"
                if track.association_id else f"object:{track.object_id}"
            )
            if tracking_key in seen:
                raise ValueError(f"duplicate track identity: {tracking_key!r}")
            seen.add(tracking_key)
            payload = self._track_payload(track)
            encoded, digest = _encode(payload, max_bytes=self.max_record_bytes)
            rows.append((
                model.model_id, model.revision, tracking_key, track.last_seen_ns,
                encoded, digest,
            ))
        with self._connection:
            self._connection.execute(
                "DELETE FROM spatial_object_tracks WHERE model_id=? AND revision=?",
                (model.model_id, model.revision),
            )
            self._connection.executemany(
                "INSERT INTO spatial_object_tracks"
                "(model_id,revision,tracking_key,last_seen_ns,payload_json,payload_sha256) "
                "VALUES(?,?,?,?,?,?)",
                rows,
            )
        return len(rows)

    def load_object_tracks(self, model_id: str, revision: str) -> tuple[ObjectTrack, ...]:
        """Load checksummed track records for one exact model revision."""
        rows = self._connection.execute(
            "SELECT tracking_key,payload_json,payload_sha256 FROM spatial_object_tracks "
            "WHERE model_id=? AND revision=? ORDER BY last_seen_ns DESC, tracking_key",
            (model_id, revision),
        ).fetchall()
        result: list[ObjectTrack] = []
        for row in rows:
            payload = _decode(
                row["payload_json"], row["payload_sha256"],
                max_bytes=self.max_record_bytes,
            )
            track = ObjectTrack(
                object_id=payload["object_id"],
                model_id=payload["model_id"],
                model_revision=payload["model_revision"],
                frame_id=payload["frame_id"],
                position_m=tuple(payload["position_m"]),
                velocity_mps=tuple(payload["velocity_mps"]),
                uncertainty_m=payload["uncertainty_m"],
                last_seen_ns=payload["last_seen_ns"],
                sensor_ids=tuple(payload["sensor_ids"]),
                modalities=tuple(payload["modalities"]),
                observation_count=payload["observation_count"],
                association_id=payload.get("association_id"),
                provenance=tuple(payload.get("provenance", ())),
                conflict=payload.get("conflict", False),
                conflict_reasons=tuple(payload.get("conflict_reasons", ())),
                conflicting_sensor_ids=tuple(payload.get("conflicting_sensor_ids", ())),
                independence_groups=tuple(payload.get("independence_groups", ())),
                position_history_m=tuple(
                    (item[0], tuple(item[1]))
                    for item in payload.get("position_history_m", ())
                ),
                position_history_sensor_ids=tuple(
                    (item[0], tuple(item[1]))
                    for item in payload.get("position_history_sensor_ids", ())
                ),
                calibration_status=payload.get("calibration_status", "unverified"),
                calibration_ids=tuple(payload.get("calibration_ids", ())),
                lineage_declared=payload.get("lineage_declared", False),
                presence_state=payload.get("presence_state", "STALE"),
                raw_observations=tuple(_observation_from_payload(item) for item in payload.get("raw_observations", ())),
            )
            key = (
                f"association:{track.association_id}"
                if track.association_id else f"object:{track.object_id}"
            )
            if key != row["tracking_key"]:
                raise ValueError("stored track key does not match its record")
            if (track.model_id, track.model_revision) != (model_id, revision):
                raise ValueError("stored track belongs to another model revision")
            result.append(track)
        return tuple(result)

    def export_portable_bundle(self, *, max_bundle_bytes: int = 100_000_000) -> bytes:
        """Export all persistent spatial state and source bytes as a checksummed bundle."""
        if isinstance(max_bundle_bytes, bool) or not isinstance(max_bundle_bytes, int) or max_bundle_bytes < 256:
            raise ValueError("max_bundle_bytes must be an integer of at least 256")
        models = self.list_models()
        records: dict[str, Any] = {
            "schema_version": 1,
            "active_model": list(self.active_model_ref()) if self.active_model_ref() else None,
            "models": [],
            "regions": [],
            "calibrations": [],
            "sensor_mounts": [],
            "source_assets": [],
            "object_tracks": [],
            "expected_sensors": [],
        }
        for model in models:
            records["models"].append({
                "model_id": model.model_id, "revision": model.revision,
                "frame_id": model.frame_id, "source_units": model.source_units,
                "source_sha256": model.source_sha256,
                "features": [{
                    "feature_id": item.feature_id, "label": item.label,
                    "position_m": list(item.position_m), "feature_type": item.feature_type,
                    "level": item.level, "zone": item.zone,
                } for item in model.features],
                "metadata": dict(model.metadata),
            })
            records["regions"].extend({
                "model_id": model.model_id, "revision": model.revision,
                "region_id": region.region_id, "label": region.label,
                "frame_id": region.frame_id, "polygon_xy_m": [list(point) for point in region.polygon_xy_m],
                "min_z_m": region.min_z_m, "max_z_m": region.max_z_m,
                "level_id": region.level_id, "zone": region.zone,
            } for region in self.load_regions(model.model_id, model.revision))
            records["source_assets"].extend({
                **{key: asset[key] for key in (
                    "model_id", "revision", "asset_id", "asset_name", "media_type",
                    "content_sha256", "metadata",
                )},
                "content_base64": b64encode(asset["content"]).decode("ascii"),
            } for asset in self.list_source_assets(model.model_id, model.revision))
            records["sensor_mounts"].extend({
                "mount_id": mount.mount_id, "sensor_id": mount.sensor_id,
                "model_id": mount.model_id, "model_revision": mount.model_revision,
                "frame_id": mount.frame_id, "source_frame_id": mount.source_frame_id,
                "translation_m": list(mount.translation_m),
                "rotation_matrix": list(mount.rotation_matrix), "verified": mount.verified,
            } for mount in self.list_sensor_mounts(model.model_id, model.revision))
            records["expected_sensors"].extend(self.load_expected_sensors(model.model_id, model.revision))
            records["object_tracks"].extend({
                "model_id": model.model_id, "revision": model.revision,
                "tracks": [self._track_payload(track) for track in self.load_object_tracks(model.model_id, model.revision)],
            })
            rows = self._connection.execute(
                "SELECT calibration_id FROM raster_calibrations WHERE model_id=? AND revision=? ORDER BY calibration_id",
                (model.model_id, model.revision),
            ).fetchall()
            for row in rows:
                calibration = self.load_calibration(row["calibration_id"])
                if calibration is not None:
                    records["calibrations"].append({
                        "calibration_id": row["calibration_id"],
                        "model_id": calibration.model_id, "model_revision": calibration.model_revision,
                        "frame_id": calibration.frame_id, "level_id": calibration.level_id,
                        "elevation_m": calibration.elevation_m,
                        "x_coefficients": list(calibration.x_coefficients),
                        "y_coefficients": list(calibration.y_coefficients),
                        "control_point_count": calibration.control_point_count,
                        "rms_residual_m": calibration.rms_residual_m,
                        "control_labels": list(calibration.control_labels),
                    })
        payload, _ = _encode(records, max_bytes=max_bundle_bytes)
        digest = sha256(payload.encode("utf-8")).hexdigest()
        envelope = json.dumps(
            {"payload": payload, "sha256": digest}, sort_keys=True,
            separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        if len(envelope) > max_bundle_bytes:
            raise ValueError(f"portable bundle exceeds {max_bundle_bytes} byte limit")
        return envelope

    def import_portable_bundle(
        self, bundle: bytes, *, activate: bool = True, max_bundle_bytes: int = 100_000_000,
    ) -> tuple[int, int]:
        """Verify and restore a portable bundle; returns (model count, asset count)."""
        if not isinstance(bundle, bytes):
            raise TypeError("portable bundle must be bytes")
        if len(bundle) > max_bundle_bytes:
            raise ValueError(f"portable bundle exceeds {max_bundle_bytes} byte limit")
        try:
            envelope = json.loads(bundle.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("portable bundle must be valid UTF-8 JSON") from exc
        if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), str):
            raise ValueError("portable bundle envelope is invalid")
        payload_text = envelope["payload"]
        if sha256(payload_text.encode("utf-8")).hexdigest() != envelope.get("sha256"):
            raise ValueError("portable bundle checksum mismatch")
        payload = _decode(payload_text, envelope["sha256"], max_bytes=max_bundle_bytes)
        if payload.get("schema_version") != 1:
            raise ValueError("unsupported portable bundle schema version")
        required_lists = ("models", "regions", "calibrations", "sensor_mounts", "source_assets", "object_tracks")
        if any(not isinstance(payload.get(key), list) for key in required_lists):
            raise ValueError("portable bundle is missing required record lists")
        if "expected_sensors" in payload and not isinstance(payload["expected_sensors"], list):
            raise ValueError("portable expected_sensors must be a list")
        models: dict[tuple[str, str], BlueprintModel] = {}
        for item in payload["models"]:
            model = BlueprintModel(
                model_id=item["model_id"], revision=item["revision"], frame_id=item["frame_id"],
                source_units=item["source_units"], source_sha256=item["source_sha256"],
                features=tuple(ModelFeature(
                    feature_id=feature["feature_id"], label=feature["label"],
                    position_m=tuple(feature["position_m"]), feature_type=feature["feature_type"],
                    level=feature.get("level"), zone=feature.get("zone"),
                ) for feature in item["features"]),
                metadata=item.get("metadata", {}),
            )
            self.save_model(model)
            models[(model.model_id, model.revision)] = model
        for item in payload["regions"]:
            self.save_region(SpatialRegion(
                item["region_id"], item["label"], item["model_id"], item["revision"],
                item["frame_id"], tuple(tuple(point) for point in item["polygon_xy_m"]),
                item["min_z_m"], item["max_z_m"], item.get("level_id"), item.get("zone"),
            ))
        for item in payload["calibrations"]:
            self.save_calibration(item["calibration_id"], RasterBlueprintCalibration(
                model_id=item["model_id"], model_revision=item["model_revision"],
                frame_id=item["frame_id"], level_id=item["level_id"],
                elevation_m=item["elevation_m"], x_coefficients=tuple(item["x_coefficients"]),
                y_coefficients=tuple(item["y_coefficients"]),
                control_point_count=item["control_point_count"],
                rms_residual_m=item["rms_residual_m"], control_labels=tuple(item["control_labels"]),
            ))
        for item in payload["sensor_mounts"]:
            self.save_sensor_mount(SensorMountTransform(
                mount_id=item["mount_id"], sensor_id=item["sensor_id"],
                model_id=item["model_id"], model_revision=item["model_revision"],
                frame_id=item["frame_id"], source_frame_id=item["source_frame_id"],
                translation_m=tuple(item["translation_m"]),
                rotation_matrix=tuple(item["rotation_matrix"]), verified=item["verified"],
            ))
        asset_count = 0
        for item in payload["source_assets"]:
            try:
                raw = b64decode(item["content_base64"], validate=True)
            except (ValueError, TypeError) as exc:
                raise ValueError("portable source asset has invalid base64 content") from exc
            if sha256(raw).hexdigest() != item["content_sha256"]:
                raise ValueError("portable source asset checksum mismatch")
            self.save_source_asset(
                item["model_id"], item["revision"], item["asset_id"],
                asset_name=item["asset_name"], media_type=item["media_type"],
                content=raw, metadata=item["metadata"],
            )
            asset_count += 1
        for item in payload.get("expected_sensors", []):
            self.save_expected_sensor(item["model_id"], item["revision"], item["sensor_id"], provider_id=item["provider_id"], region_ids=tuple(item["region_ids"]), max_age_ns=item["max_age_ns"])
        for item in payload["object_tracks"]:
            key = (item["model_id"], item["revision"])
            if key not in models:
                raise ValueError("portable track set references an unknown model revision")
            tracks = tuple(self._track_from_payload(track) for track in item["tracks"])
            self.save_object_tracks(models[key], tracks)
        active = payload.get("active_model")
        if activate and active is not None:
            if not isinstance(active, list) or len(active) != 2 or tuple(active) not in models:
                raise ValueError("portable active model reference is invalid")
            self.set_active_model(active[0], active[1])
        return len(models), asset_count

    def append_sensor_lifecycle_event(
        self, event: dict[str, Any], *, max_events: int = 1000
    ) -> None:
        """Persist one validated sensor lifecycle event, retaining a bounded tail."""
        if not isinstance(event, dict):
            raise TypeError("sensor lifecycle event must be a dictionary")
        if isinstance(max_events, bool) or not isinstance(max_events, int) or max_events < 1:
            raise ValueError("max_events must be a positive integer")
        payload = dict(event)
        if not isinstance(payload.get("provider_id"), str) or not payload["provider_id"].strip():
            raise ValueError("sensor lifecycle event requires provider_id")
        if not isinstance(payload.get("state"), str) or not payload["state"].strip():
            raise ValueError("sensor lifecycle event requires state")
        encoded, digest = _encode(payload, max_bytes=self.max_record_bytes)
        with self._connection:
            self._connection.execute(
                "INSERT INTO sensor_lifecycle_events(payload_json,payload_sha256) VALUES(?,?)",
                (encoded, digest),
            )
            self._connection.execute(
                "DELETE FROM sensor_lifecycle_events WHERE event_id NOT IN "
                "(SELECT event_id FROM sensor_lifecycle_events ORDER BY event_id DESC LIMIT ?)",
                (max_events,),
            )

    def load_sensor_lifecycle_events(self, *, limit: int = 1000) -> tuple[dict[str, Any], ...]:
        """Load the newest persisted lifecycle events in chronological order."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        rows = self._connection.execute(
            "SELECT payload_json,payload_sha256 FROM sensor_lifecycle_events "
            "ORDER BY event_id DESC LIMIT ?", (limit,)
        ).fetchall()
        events = [
            _decode(row["payload_json"], row["payload_sha256"], max_bytes=self.max_record_bytes)
            for row in reversed(rows)
        ]
        return tuple(events)

    def set_sensor_alert_acknowledgement(
        self, alert_id: str, *, acknowledged: bool,
        acknowledged_at_utc: str | None = None, acknowledged_by: str = "operator",
    ) -> None:
        """Persist or clear an acknowledgement for one active alert incident."""
        if not isinstance(alert_id, str) or not alert_id.strip():
            raise ValueError("alert_id must be a non-empty string")
        if not isinstance(acknowledged, bool):
            raise TypeError("acknowledged must be a boolean")
        if not isinstance(acknowledged_by, str) or not acknowledged_by.strip():
            raise ValueError("acknowledged_by must be a non-empty string")
        with self._connection:
            if not acknowledged:
                self._connection.execute(
                    "DELETE FROM sensor_alert_acknowledgements WHERE alert_id=?", (alert_id,)
                )
                return
            payload = {
                "alert_id": alert_id,
                "acknowledged": True,
                "acknowledged_at_utc": acknowledged_at_utc,
                "acknowledged_by": acknowledged_by,
            }
            encoded, digest = _encode(payload, max_bytes=self.max_record_bytes)
            self._connection.execute(
                "INSERT INTO sensor_alert_acknowledgements(alert_id,payload_json,payload_sha256) "
                "VALUES(?,?,?) ON CONFLICT(alert_id) DO UPDATE SET "
                "payload_json=excluded.payload_json,payload_sha256=excluded.payload_sha256",
                (alert_id, encoded, digest),
            )

    def load_sensor_alert_acknowledgements(self) -> dict[str, dict[str, Any]]:
        """Load integrity-checked alert acknowledgements keyed by alert incident ID."""
        rows = self._connection.execute(
            "SELECT alert_id,payload_json,payload_sha256 FROM sensor_alert_acknowledgements "
            "ORDER BY alert_id"
        ).fetchall()
        result = {}
        for row in rows:
            payload = _decode(
                row["payload_json"], row["payload_sha256"], max_bytes=self.max_record_bytes
            )
            if payload.get("alert_id") != row["alert_id"] or payload.get("acknowledged") is not True:
                raise ValueError("stored sensor alert acknowledgement is inconsistent")
            result[row["alert_id"]] = payload
        return result

    def clear_inactive_sensor_alert_acknowledgements(self, active_alert_ids: set[str]) -> None:
        """Forget acknowledgements for incidents no longer present in the current snapshot."""
        if not isinstance(active_alert_ids, set) or any(
            not isinstance(item, str) for item in active_alert_ids
        ):
            raise TypeError("active_alert_ids must be a set of strings")
        with self._connection:
            if not active_alert_ids:
                self._connection.execute("DELETE FROM sensor_alert_acknowledgements")
                return
            placeholders = ",".join("?" for _ in active_alert_ids)
            self._connection.execute(
                f"DELETE FROM sensor_alert_acknowledgements WHERE alert_id NOT IN ({placeholders})",
                tuple(sorted(active_alert_ids)),
            )

    def close(self) -> None:
        self._connection.close()
