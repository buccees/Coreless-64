"""Persistent SQLite registry for validated VIGIL models, regions, and raster calibrations.

The database stores normalized spatial metadata only; original drawings/images and
sensor payloads remain separate. Records are deterministic JSON with SHA-256
integrity checks, SQL-bound parameters, size limits, and immutable model/region
identities. Revisions must change when geometry changes.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
import sqlite3
from typing import Any

from .blueprint import BlueprintModel, ModelFeature, _validate_vector
from .raster_calibration import RasterBlueprintCalibration
from .spatial_regions import SpatialRegion


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
            CREATE TABLE IF NOT EXISTS raster_calibrations (
                calibration_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                revision TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_raster_calibration_model
                ON raster_calibrations(model_id, revision, calibration_id);
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

    def close(self) -> None:
        self._connection.close()
