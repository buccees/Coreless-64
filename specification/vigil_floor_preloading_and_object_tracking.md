# VIGIL adjacent-floor preloading and object tracking

## Adjacent floor window

When a connected `BuildingBlueprint` is activated, the workspace prepares a render-ready `BlueprintView` for every registered floor. `preload_adjacent_floors()` exposes the active floor plus the immediately lower and higher floors, ordered by surveyed elevation. A viewer can keep those views mounted before a stair/elevator transition and switch the active layer without waiting for blueprint geometry to be parsed or projected.

The floor window is geometry preloading, not proof of location. Automatic floor transitions still require fresh, calibrated position estimates and a registered vertical connection. Floors need correct shared-frame transforms and surveyed elevations; missing or incorrectly aligned floor data must not be guessed.

## Object tracking boundary

`ObjectObservation` represents a sensor adapter's object detection after it has been converted into the active model's coordinate frame. It carries a stable object ID, sensor ID, timestamp, uncertainty, modality, and provenance. `ObjectTracker` fuses same-object detections by inverse variance, applies a bounded position filter, estimates velocity, expires stale tracks, and rejects observations from another model revision or coordinate frame. The workspace exposes current tracks in `WorkspaceSnapshot.object_tracks`.

### The 2.4 GHz terminology matters

2.4 GHz is a radio-frequency band, not acoustic sonar. The implementation names this modality `rf_2_4ghz` for RF ranging/detection supplied by a real adapter, and `acoustic_sonar` for acoustic time-of-flight sonar. They are distinct inputs and must not be treated as interchangeable. The current code provides tracking primitives and an adapter boundary; it does not include radio hardware drivers, acoustic transducers, ranging firmware, or an assertion that ordinary 2.4 GHz Wi-Fi can accurately range objects by itself.

For usable ranging, the sensor subsystem must produce calibrated positions (or a future range-to-position solver must consume range measurements and known anchor geometry), attach uncertainty and timestamps, and transform results into the active building frame. Multiple sensors, occlusion handling, object identity continuity, and site-specific calibration will be needed for robust real-world tracking.
