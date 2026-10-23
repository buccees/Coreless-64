# VIGIL Spatial Awareness — Coreless-64 Integration

## Purpose

VIGIL needs a spatial-awareness subsystem that locates a device or tracked subject *within a registered 3D blueprint/model*. This is not a turn-by-turn navigation feature. It aligns observations and positioning estimates with model geometry and reports a confidence-bounded pose to VIGIL.

Implementation belongs in `buccees/Coreless-64`. The separate VIGIL repository is reference material only.

## Architectural boundary

Keep the subsystem behind explicit interfaces so it can be tested without GPS hardware, a camera, or a physical facility.

- **Blueprint ingestion**: accepts a blueprint/image/PDF or a 3D model through a format-specific adapter; validates units, scale, orientation, levels, and coordinate metadata.
- **Model registry**: stores the normalized model, its revision/hash, coordinate frame, floor/zone identifiers, and known anchors.
- **Observation adapters**: provide timestamped GPS/GNSS, IMU, camera/visual features, BLE/UWB/beacon, or manually confirmed anchor observations when available. Missing sensors must remain missing, not be fabricated.
- **Pose estimator**: combines compatible observations with model anchors and returns a pose estimate, uncertainty, timestamp, and provenance.
- **Spatial query API**: answers model-relative questions such as current level/zone, nearest modeled feature, distance to a model feature, and whether a pose intersects a defined region.
- **VIGIL presentation adapter**: exposes the pose and confidence for a green-phosphor terminal, facility overlay, and alerts without owning sensor acquisition or authoritative Coreless policy.

## Coordinate frames

Use named, explicit frames; never mix raw GPS coordinates with model-local coordinates implicitly.

1. **Geodetic frame** — GNSS/GPS observations in a documented datum.
2. **Facility frame** — a site-wide metric coordinate system, if a surveyed/georeferenced transform exists.
3. **Model frame** — the blueprint's normalized local coordinates and units.
4. **Device frame** — sensor/body coordinates, with declared axis conventions.

A versioned transform maps geodetic/facility coordinates to the model frame only when calibration or surveyed control points support it. Store transform provenance and calibration residuals. If the blueprint has no georeference, require anchor-based/manual alignment; do not pretend GPS alone identifies an indoor position.

## Pose and confidence contract

A pose result should include:

- model ID and immutable model revision/hash;
- coordinate-frame ID and position in model units;
- optional orientation, level, and zone;
- observation timestamp and result timestamp;
- source observations/adapter identifiers and their timestamps;
- estimated uncertainty/confidence and validity state;
- stale-data indicators and reason codes when a fix is unavailable.

Use explicit states such as `UNINITIALIZED`, `CALIBRATING`, `TRACKING`, `DEGRADED`, and `LOST`. Do not present a stale or low-confidence estimate as an exact location. A caller must be able to distinguish “no fix” from a valid pose at the origin.

## Coreless integration rules

- Route sensor data through the existing versioned Coreless input/event boundary or a narrowly defined adapter; do not bypass sequence, timestamp, metadata, and provenance validation.
- Spatial interpretation is derived data. Malformed or unavailable VIGIL interpretation must not block delivery of raw Coreless input events.
- Keep AI output advisory. A model-generated interpretation cannot authorize movement, unlocks, alarms being silenced, or other protected actions.
- Persist model metadata and calibration records through an explicit storage interface; keep large source assets and retention policy separate from transient pose state.
- Use deterministic fake observations and a synthetic model for regression tests. Hardware adapters and real-world accuracy require separate validation.

## Suggested interface shape

These are conceptual contracts to implement and test, not claims that the APIs already exist:

- `BlueprintSource.load(source) -> BlueprintAsset`
- `ModelNormalizer.normalize(asset, calibration) -> ModelRevision`
- `ObservationProvider.read() -> ObservationBatch`
- `PoseEstimator.update(model_revision, observations, prior_pose) -> PoseEstimate`
- `SpatialQuery.evaluate(model_revision, pose_estimate, query) -> QueryResult`
- `VigilSpatialAdapter.snapshot() -> SpatialStatus`

Concrete names may follow repository conventions discovered during implementation. Avoid introducing a parallel event bus if existing Coreless input and component interfaces can carry the contract cleanly.

## Initial implementation sequence

1. Inspect existing VIGIL adapter, Coreless input-event ABI, storage conventions, and terminal/display interfaces on the active integration branch.
2. Add typed model-frame, transform, observation, pose, uncertainty, and status records.
3. Implement a synthetic blueprint/model and deterministic fake-observation provider.
4. Add tests for frame conversion, unit/scale validation, stale observations, missing sensors, invalid calibration, uncertainty propagation, and no-fix behavior.
5. Add the VIGIL read-only status adapter and a minimal terminal panel for model/floor/zone, pose state, confidence, and last update.
6. Add real blueprint parsing and sensor adapters individually, each with explicit format/device validation.
7. Validate against surveyed control points and representative indoor/outdoor tests before claiming positional accuracy.

## Acceptance criteria

- A user can load/register a model and see which model revision is active.
- The system can express a position in model coordinates only after a valid calibration/alignment step.
- GPS is treated as one possible observation source, not a sufficient indoor-positioning solution.
- Unknown, stale, inconsistent, or poorly calibrated observations produce degraded/no-fix status rather than a fabricated precise location.
- Spatial results include frame, timestamp, uncertainty, and provenance.
- Raw Coreless input delivery continues if the optional VIGIL spatial adapter fails.
- Unit tests run without physical devices; hardware and field accuracy are separately reported.
- The terminal presentation is read-only with respect to Coreless security policy.

## Non-goals for the first milestone

- Turn-by-turn navigation as the primary feature.
- Claiming centimeter-level or indoor accuracy from GPS alone.
- Treating a scanned 2D blueprint as a fully registered 3D model without scale, elevation/floor, and alignment data.
- Allowing AI-generated pose or text to bypass deterministic Coreless permissions.

## Optional live sensor-provider boundary

The workspace exposes `register_sensor_provider(provider_id, provider)`, `poll_sensors()`, and `unregister_sensor_provider(provider_id)`. A provider implements a small `read() -> Sequence[SpatialObservation]` contract. Each observation must already include its model ID/revision, target frame, monotonic timestamp, uncertainty, and provenance. The workspace does not silently transform raw device coordinates or infer a missing fix.

Providers are polled independently. A disconnected or malformed adapter returns an `ERROR` status for that provider without aborting the remaining polls or throwing into the caller's input loop. The pose estimator still rejects stale and incompatible observations. This is an adapter seam and testable lifecycle—not yet a live GPS, camera, IMU, UWB, or RF hardware driver. Coreless continues to own raw touch/pointer/input handling, and VIGIL provider health must never gate those events.

## Scanned floor-plan alignment

`vigil/raster_calibration.py` adds a deterministic affine calibration for a scanned 2D floor plan. An operator or upstream detector supplies at least three non-collinear control points pairing image pixel coordinates with surveyed model-frame XY coordinates. The fitted transform reports its RMS residual, maps pixels to metric floor coordinates at an explicit surveyed elevation, and supports the inverse model-to-pixel mapping for overlays.

This calibrates the image coordinate system; it does **not** yet load PDF/image files, detect walls or labels, infer geometry, or reconstruct a 3D building. Those require format-specific import/vision adapters and review of detected geometry. A floor plan without known scale/orientation/control points must remain uncalibrated rather than being positioned by guesswork.

## Infrared floor mapping

`vigil/infrared_floor_mapping.py` adds a calibrated adapter for mapping infrared/thermal pixel samples onto a registered floor-plan coordinate frame. It takes an explicit sensor ID, image dimensions, a matching raster calibration (model/revision/frame/floor/elevation), timestamped frame samples, normalized intensity, and optional calibrated temperature values. Each mapped sample includes metric coordinates and an uncertainty estimate that combines calibration RMS residual with pixel-localization uncertainty scaled into meters. Samples outside the calibrated image and invalid timestamps/intensities are rejected.

This is the geometry and metadata boundary for an IR overlay—not a camera driver, raw thermal-image decoder, automatic heat-map segmenter, or a claim that temperature is available from every infrared sensor. An upstream adapter must decode the sensor's actual output and supply calibrated values. The renderer can use the mapped points to overlay warm/cool detections on the active floor plan; image-to-floor calibration and sensor mounting alignment remain prerequisites. Infrared detections are an additional observation layer and must not replace Coreless raw input or be treated as an authoritative safety decision.


## Unified multimodal provider contract

Optional sensor providers may return a `SensorBatch` containing calibrated pose observations, object detections, and infrared floor maps in one poll. The workspace routes position observations to pose estimation, object detections to the shared object tracker, and infrared maps to the per-floor overlay store plus labeled-object ingestion. Legacy position-only providers remain supported. Provider failures are isolated and reported per provider; raw Coreless pointer/touch input remains independent. All data must be calibrated to the active model revision/frame, and infrared maps must reference a registered floor for composed buildings.


## Spatial Intelligence Overdrive / quality-gated finisher

`vigil/spatial_scene.py` assembles a render-ready scene from the active model, compatible pose, current object tracks, and calibrated infrared overlays. Its `SpatialScene` report exposes individual deterministic checks and a final readiness result. The green terminal can display **FATALITY // SPATIAL SCENE LOCKED** only when the blueprint view builds, pose model/revision/frame match, the pose is fresh and sufficiently certain in a usable tracking state, and active tracks have no unresolved conflicts. Otherwise it displays **FATALITY DENIED // VALIDATION INCOMPLETE** with explicit failed checks.

Infrared overlays are reported when available but are not required for readiness, since a missing optional sensor must not fabricate data or disable the rest of VIGIL. Stale or frame-mismatched tracks are excluded from the assembled scene. This is a visualization/diagnostic gate only: the finishing banner does not authorize movement, unlocks, alarms, or any protected Coreless action. It is a named dramatic terminal state earned by validation, not a substitute for Coreless policy.

## Implemented confidence-aware spatial query API

`vigil/spatial_query.py` provides `SpatialQueryEngine` bound to one validated immutable blueprint revision. It evaluates a `PoseEstimate` against model identity, revision, coordinate frame, observation time, freshness, tracking state, and a configurable uncertainty threshold. Valid results report model-frame position, nearest feature and distance, that feature's level/zone, and optionally feature IDs within a caller-supplied radius.

The result status explicitly distinguishes `OK`, `DEGRADED`, `NO_FIX`, `STALE`, `FUTURE_TIMESTAMP`, and `MODEL_MISMATCH`. A stale or mismatched pose cannot produce a misleading nearest-feature result. A degraded but fresh pose may return its best estimate while clearly labeling the result degraded. A missing fix is distinct from a valid position at the origin.

This API is deterministic software over registered feature points. It does not infer polygonal room boundaries, parse raw CAD/PDF/mesh files, discover sensors, or prove physical tracking accuracy. Region-intersection queries require an explicitly modeled region representation and remain separate work.
