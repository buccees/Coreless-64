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

Use one monotonic clock domain for all live observation timestamps, freshness checks, and snapshot generation. The operator endpoint uses `time.monotonic_ns()` to match the sensor-observation contract; wall-clock epoch timestamps must not be compared directly to monotonic sensor times. Persisted tracks restored after a reboot remain `REACQUIRE` until fresh observations establish a new live timeline.

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

## Explicit spatial regions and membership queries

`vigil/spatial_regions.py` adds `SpatialRegion`, a versioned polygon in model-frame XY coordinates with an explicit vertical interval, plus optional level/zone labels. `query_region()` checks model/revision/frame alignment and pose freshness/quality before reporting membership. Boundary points are treated as inside within a small explicit numerical tolerance. When pose is absent, stale, future-dated, or frame-mismatched, `inside` is `None` rather than a guessed true/false result.

Regions must be explicitly supplied in calibrated meter coordinates; they are not inferred from a feature label, raster image, or AI text. The current polygon contract checks vertex validity and non-zero area; full CAD topology repair and arbitrary polygon self-intersection validation remain future geometry-import work.

## Persistent spatial registry

`vigil/spatial_registry_store.py` adds a SQLite-backed record store for normalized blueprint revisions, explicit polygon regions, raster calibration metadata, bounded object tracks, and checksummed source assets. Records use parameterized SQL, canonical JSON, record-size limits, and SHA-256 integrity checks. A model revision is immutable within the store; changed geometry or calibration requires a new revision/record ID. The store separately remembers the active model revision. Source assets are stored as separate immutable byte records tied to a model revision, with a media type, name, metadata, and content checksum. Workspace imports preserve the exact original JSON manifest alongside its normalized model. The default per-record limit is 5 MB; arbitrary image/CAD ingestion pipelines and raw sensor-payload archival are still not implemented. `SpatialRegistryStore.export_portable_bundle()` now emits a deterministic, checksummed bundle containing all registered model revisions, regions, raster calibrations, sensor mounts, source asset bytes, bounded object tracks/history, and the active-model pointer. `import_portable_bundle()` validates the envelope and payload checksum, enforces a total bundle-size limit, verifies source-asset checksums, and restores the records into another registry. This is a registry-level portable bundle; integration into the full Coreless OS/SSD snapshot, boot, and copy lifecycle remains open.

`SpatialWorkspace(registry_store=...)` saves imported/activated models and registered regions. It also persists the bounded last-known object-track set for each model revision, including position history and evidence metadata. On restart, tracks are restored as `REACQUIRE` rather than treated as live sensor contact; fresh compatible observations are required before they become current again. Live raw sensor observations and pose estimates remain transient and must be reacquired. Raster calibrations can be saved and retrieved through `SpatialRegistryStore`. `SpatialWorkspace.ingest_calibrated_infrared_pixels(...)` now loads a saved calibration by ID, rejects calibrations that do not match the active model revision/frame, maps a timestamped pixel batch, and routes the resulting map into workspace ingestion. The IR map retains the calibration ID and supplied sensor-mount ID as provenance. Separately, `SensorMountTransform` now models an explicit rigid sensor-local-to-model-frame transform (3×3 proper rotation plus translation), and `SpatialRegistryStore` persists immutable mount records tied to a model revision with integrity checks. `SpatialWorkspace.ingest_sensor_local_object_observations(...)` deliberately applies a selected saved transform only to observations identified as sensor-local, validates sensor/model/revision/source-frame identity, and attaches mount provenance and calibration status. This prevents accidental double transforms of observations already in model coordinates. The transform must be supplied from actual calibration/survey data; code validation does not prove physical mount accuracy. Raw camera/thermal image decoding remains an upstream adapter responsibility.

## Authenticated live operator overlay

`vigil/spatial_snapshot.py` defines the version-1, JSON-safe `build_spatial_snapshot(workspace, now_ns=...)` contract. Nanosecond timestamps are emitted as decimal strings to avoid JavaScript precision loss. Snapshot data includes the active model/revision/frame, visible floor features and coordinate bounds, pose status/freshness, current/last-known object locations, bounded motion trails, speed/state, uncertainty/source lineage, and region membership with `inside=null` when the pose cannot support an answer.

The HTTPS LAN service exposes this through authenticated, GET-only `/api/vigil/spatial`. The browser page displays the provided geometry and markers; it does not generate object coordinates. A missing or invalid snapshot becomes a visible error/empty state. The server CLI accepts `--spatial-db` (defaults to a registry file beside the machine image) and optional `--blueprint` (a versioned JSON manifest to load and persist). The server still requires TLS certificate/key and the configured operator password.

This is a software integration milestone, not hardware proof. To see live positions, the workspace must have a calibrated blueprint, a compatible live sensor adapter that emits model-frame observations, and aligned timestamps. A blank map, no-fix, stale marker, or degraded state is an intentional truthful result, not fabricated tracking.

The version-1 spatial snapshot also exposes per-track evidence metadata to the authenticated operator view: observation count, source provenance, declared independence groups, calibration status and calibration IDs, and whether source lineage is declared. These fields describe the evidence supplied by adapters; they do not independently certify a sensor or calibration. The operator cards display this metadata alongside position, speed, age, uncertainty, source sensors, and modality. Older clients may ignore these additive fields.


## Current implementation checkpoint — 2026-10-23

The spatial snapshot and operator cards now expose object evidence provenance, observation counts, declared independence groups, calibration IDs/status, lineage declaration, and per-provider `UNPOLLED`/`ONLINE`/`ERROR` health. The store persists bounded object tracks and history; workspace restart restores them as `REACQUIRE` until fresh compatible observations arrive. The authenticated spatial endpoint uses monotonic nanoseconds to match observation timestamps. CI passed for the endpoint fixture commit `76cff07`; a prior implementation-only run failed because the matching test fixture was not yet updated. Confirm the newest workflow after current documentation changes. The product gates still open are physical measurement/validation of sensor-mount transforms, concrete sensor drivers, full portable snapshot/copy integration, and real calibrated field validation.
### Raw per-sensor object evidence

The version-1 spatial snapshot now adds `sensor_observations` to each object track. Each bounded, deduplicated record retains the individual adapter-reported sensor ID, modality, monotonic timestamp and age, model-frame position, uncertainty, provenance, declared independence group, calibration status/IDs, and lineage declaration. The operator inspector presents these rows beside the fused track estimate and computes each reported position's distance from that current estimate; this residual is a comparison aid, not a claim that the estimate is ground truth. Sensors implicated in a reported track conflict are highlighted for review.

Raw object observations are retained on the track with a bounded history and serialized in the registry record and portable bundle. This is **structured detection metadata**, not raw camera frames, thermal images, RF waveforms, or a direct hardware capture stream. The operator can compare only the measurements supplied by installed adapters. Repeat polling of identical observations is deduplicated; distinct timestamps or changed measurements remain separate records. Older stored records without this additive field continue to load with an empty raw-observation history.


### Per-sensor quality and fusion disposition

Each retained object measurement now includes a derived quality_status (FRESH, STALE, UNCALIBRATED, CONFLICTING, or TIME_UNCERTAIN), additive quality_flags, and a fusion_disposition with a plain-language note. Historical measurements are explicitly labeled HISTORICAL_ONLY; current clean-epoch measurements are labeled as contributing to fusion; measurements involved in a conflict are marked as the conflict winner or not selected based on the tracker's lowest-uncertainty conflict policy. Quality flags are caveats, not automatic rejection rules: the tracker currently may use an uncalibrated measurement, and the UI must not imply it was excluded.

A sensor is not called MISSING merely because it has no row in an object track. That claim requires an explicit expected-sensor configuration and a coverage/association contract; until then the UI distinguishes no observation from a confirmed sensor outage. Provider health (UNPOLLED/ONLINE/ERROR) remains a separate adapter-level signal.


### Correlated-feed-aware object fusion

For a single measurement epoch, the object tracker now groups readings by their declared evidence-independence lineage. All raw detections remain in the bounded evidence ledger, but only the lowest-uncertainty reading from each lineage group contributes to the position estimate and its inverse-variance uncertainty. Conflict checks likewise compare representatives from distinct lineage groups, so two derived feeds from one physical source cannot independently manufacture a disagreement or extra confidence. Equal-uncertainty ties are resolved deterministically by sensor ID and object ID. If adapters omit lineage, the existing sensor-ID fallback remains a compatibility convention—not proof of physical independence. This change does not prove that different declared groups are truly independent; that remains the responsibility of sensor adapters and deployment configuration.


### Health-aware track validity

The operator snapshot exposes `track_validity` separately from object presence and raw measurement quality. `CURRENT` means the last measurement is within the configured age limit, calibration is verified, and no unresolved conflict is recorded. `DEGRADED` means the estimate is recent but has an unresolved sensor conflict or non-verified calibration. `STALE_LAST_KNOWN` means the last measurement exceeds the age limit; its last-known coordinates and evidence history remain available and must not be interpreted as proof the object departed. `REACQUIRE` marks restored tracks awaiting new compatible sensor contact, and `TIME_UNCERTAIN` marks a future-dated track timestamp.

`track_validity_reasons` explains every applicable caveat, including calibration failure versus unverified calibration. This is a display/interpretation contract, not a claim that failed-calibration observations were automatically excluded from fusion. Sensor absence is not inferred from a missing observation row; confirmed offline/missing status still requires explicit expected-sensor and coverage configuration.


## Expected-sensor coverage accounting

The workspace can explicitly register an expected sensor, its provider, one or more modeled spatial regions, and a freshness limit. The spatial snapshot reports `UNPOLLED`, `PROVIDER_DISCONNECTED`, `PROVIDER_ERROR`, `TIME_UNCERTAIN`, `REPORTING_IN_SCOPE`, `STALE_REPORT`, or `NO_REPORT_IN_SCOPE` based on provider lifecycle and timestamped observations from that sensor inside its declared region(s). An observation outside the polygon or vertical interval does not satisfy that region's expectation. Expectations are opt-in: absence of a row does not itself imply sensor failure or object absence. This is a reporting contract, not a guarantee that a physical sensor can see the whole region; field of view, occlusion, calibration, and driver health require independent validation. Expected-sensor declarations are persisted against their exact model revision in the registry and portable bundles. Provider connections and live readings remain runtime state.


### Persistent expected-sensor configuration

Expected-sensor declarations can be stored in the SQLite spatial registry against an exact model ID and revision. The registry validates that each declared region exists in that same revision, checksummed records protect the saved declaration, workspace activation restores the matching declarations, and unregistering a declaration removes it from persistent storage. Portable registry bundles include expected-sensor declarations so the machine's configured reporting contract can travel with its spatial model. Provider connections and live readings remain runtime state and are not persisted as if they were live after restart. A restored declaration starts as `UNPOLLED` until its provider is registered and polled again.


### Provider lifecycle and recovery

Each provider lifecycle record preserves the last successful poll timestamp, consecutive failure count, latest state, and latest error. A successful poll resets the failure counter and updates last-success time; failures increment the counter without erasing the last known successful timestamp. Unregistering a provider leaves an explicit `DISCONNECTED` lifecycle record so expected coverage can distinguish a deliberately disconnected adapter from one that has never been polled. Re-registering begins at `UNPOLLED` while retaining the previous successful-poll timestamp for diagnosis. These are runtime monotonic timestamps and are not treated as persistent wall-clock times across reboot. Sensor recovery indicates adapter reads are succeeding again, not that physical calibration or coverage has been verified.
 A stale report means an observation exists inside the declared region but its age exceeds that sensor expectation's freshness limit; no report means no retained in-scope observation exists. This distinction describes telemetry recency, not object presence or physical sensor visibility.

### Sensor health alerts and transition history

The runtime snapshot exposes derived `sensor_health_alerts` for provider errors/disconnections and expected sensors that are stale, overdue, time-uncertain, or reporting failures. These alerts are recomputed from current runtime status and expected-coverage declarations, so they clear when the corresponding condition recovers. A bounded `sensor_lifecycle_history` records provider state transitions, failure counts, errors, monotonic timestamps, and UTC recording timestamps; when a `SpatialRegistryStore` is configured, the most recent 1,000 events are persisted with record checksums and restored when a workspace starts. Monotonic timestamps are only meaningful within their original boot/session; `recorded_at_utc` is the cross-restart chronology field and follows the host wall clock. Without a configured registry store, history remains runtime-only. Alert severity is an operator triage hint, not a safety certification. No alerts are synthesized for undeclared sensors.


## Persistent sensor-health alert acknowledgements

- Sensor-health alerts in the authenticated spatial snapshot have deterministic incident IDs derived from source, provider, sensor (when applicable), and alert state.
- When a persistent `SpatialRegistryStore` is configured, an authenticated operator can acknowledge an active alert through `POST /api/vigil/alerts/acknowledge`. The endpoint enforces session authentication, same-origin requests, payload limits, and active-alert validation.
- Acknowledgement records are stored in SQLite with integrity-checked JSON payloads, UTC timestamp, and actor label. The snapshot exposes acknowledgement status and metadata to the operator display.
- Acknowledgements are cleared when a subsequent snapshot observes that the corresponding alert is no longer active, so a later recurrence can require a new acknowledgement. If no snapshot observes the recovery interval, the system cannot infer that a distinct incident occurred; incident identity is limited by the currently available state-transition evidence.
- Acknowledgement is an operator workflow marker, not a repair action and not proof that the sensor has recovered. Without a persistent registry, the acknowledgement endpoint returns an explicit unavailable response.
