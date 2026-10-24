# Side Quests

Optional explorations that complement Coreless-64 and VIGIL without silently displacing the main machine-development priorities.

## VIGIL Eye — modular optical sensor head and wearable sensor harness

**Status:** Captured; equipment selection and prototyping not yet started.

**Tracking issue:** [#22 — Side quest: VIGIL Eye — modular optical sensor head](https://github.com/buccees/Coreless-64/issues/22)

### Concept

A replaceable, eye-like optical module inspired by the single-eye silhouette in *Alien: Earth*, integrated into a wearable behind-the-neck/shoulder harness with a belt pouch. The eye houses the forward-facing camera and may carry additional sensors. The module provides real sensor evidence to VIGIL's spatial-awareness system; it is not the Coreless-64 machine or the spatial intelligence itself.

### Equipment list — first prototype

This is a planning list, not a claim that the parts have been purchased or tested. Choose exact models after confirming interfaces, power draw, field of view, weight, and budget.

#### Visual input and spatial sensing

- [ ] **Camera module** — required; USB UVC camera for easiest first integration, or a compatible CSI camera if the chosen controller supports it.
- [ ] **Eye enclosure and camera mount** — protects the camera and aims it forward; provide adjustment for field of view and calibration.
- [ ] **IMU (accelerometer + gyroscope)** — measures harness movement and orientation; select a module with a documented interface such as I²C or SPI.
- [ ] **Distance sensor** — one ToF/LiDAR-style sensor for basic range measurements; confirm useful outdoor range and sunlight performance for the intended use.
- [ ] **Optional stereo/depth camera** — consider only if monocular camera plus range sensor does not meet localization needs.
- [ ] **Optional microphone array** — audio input, if sound direction or audio capture is in scope.
- [ ] **Optional environmental sensor** — temperature/humidity/pressure or air-quality module, selected for a specific use case rather than adding every sensor by default.

#### Controller, wireless, and data

- [ ] **Arduino-compatible controller / ESP32 development board** — handles compatible low-bandwidth sensors and simple control tasks. It is not assumed to run the full VIGIL vision workload.
- [ ] **Compute unit for camera processing** — required if image processing runs on the wearable; choose a small Linux-capable SBC or another compute platform based on camera interface and processing needs.
- [ ] **Wi-Fi interface / antenna(s)** — use the controller's certified onboard radio or a compatible external Wi-Fi adapter/antenna arrangement; avoid assuming multiple antennas automatically create a working “array.”
- [ ] **USB data hub or interface board** — only if required by the selected camera and peripherals.
- [ ] **Storage** — appropriately sized microSD/SSD for logs and captures, with write endurance considered.
- [ ] **Cables and connectors** — locking connectors where practical, strain relief, labeled sensor leads, and service loops at moving joints.

#### Power and mounting

- [ ] **Rechargeable battery pack** — sized after measuring total load and desired runtime; use a protected pack from a reputable supplier.
- [ ] **Battery-management / protection and regulated DC-DC converters** — correct voltage rails, current capacity, fuse/overcurrent protection, and low-battery monitoring.
- [ ] **Power switch and accessible disconnect** — reachable without removing the harness.
- [ ] **Behind-the-neck shoulder harness** — padded, adjustable, load-spreading frame with no pressure on the throat or restricted head movement.
- [ ] **Belt pouch** — carries battery and compute/storage modules; include ventilation, retention, and cable exits.
- [ ] **Mounting hardware** — camera bracket, sensor brackets, screws, standoffs, hook-and-loop or strap retainers, and cable clips.
- [ ] **Thermal management** — ventilation and temperature checks for enclosed compute and battery components.
- [ ] **Basic test equipment** — multimeter, USB power meter, and a way to log power draw and sensor timestamps.

### Suggested data path

**Camera → compute unit → VIGIL visual-processing/provider interface**

**IMU + distance/environmental sensors → Arduino/ESP32 or compatible interface → compute unit**

**Compute/controller ↔ Wi-Fi ↔ external input/output**

**Battery → protected power distribution → individually regulated rails for compute, camera, controller, and sensors**

Keep sensor signal voltage and supply rails compatible. Do not power motors, high-current compute, or a camera directly from a microcontroller pin. Validate the battery, charging arrangement, fuse, thermal behavior, and connector polarity before wearing the prototype.

### Planned work

- [ ] Confirm intended camera field of view, working distance, lighting, and whether depth sensing is needed.
- [ ] Choose the camera and compute platform first; then match controller, sensor buses, Wi-Fi, power rails, and enclosure to them.
- [ ] Define mount, field of view, lighting, calibration, timestamps, coordinate frame, provenance, and provider-health reporting.
- [ ] Integrate a simulated sensor provider before hardware selection.
- [ ] Bench-test each sensor separately; measure latency, coverage, range accuracy, blind spots, power draw, and reacquisition.
- [ ] Build and test the shoulder harness and belt pouch with dummy weights before wearing powered electronics.
- [ ] Design the eye-like enclosure around validated sensor, power, and thermal requirements.

### Acceptance criteria

- Observations enter VIGIL through a documented provider interface with timestamps and provenance.
- Calibration and sensor pose are explicit; estimates are not represented as ground truth.
- Loss of view/provider failure is distinguishable from evidence that an object is absent.
- The optical head can be replaced without redesigning the Coreless-64 machine.
- Accuracy, runtime, and coverage claims are backed by physical tests, not only simulation or CI.

### Constraints

A single camera only sees its available field of view. Broader awareness requires additional sensors or other evidence sources. A microcontroller alone may not have enough compute for camera-based vision; separate the sensor interface from the vision compute if needed. Keep this side quest from displacing the main boot, host-I/O, and runtime-validation work.
