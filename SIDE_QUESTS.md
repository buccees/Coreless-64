# Side Quests

Optional explorations that complement Coreless-64 and VIGIL without silently displacing the main machine-development priorities.

## VIGIL Eye — modular optical sensor head and wearable sensor harness

**Status:** Captured; equipment selection and prototyping not yet started.

**Project record:** This plan now lives in the Side Quests documentation and Experimental Features website section. The original GitHub issue is retained as closed history, not an active task tracker.

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

### Comprehensive modular equipment and verification checklist

This expands the first-prototype list into a full planning checklist. It is **not a purchase order**: no part is assumed to be owned, selected, or physically tested. Exact models and quantities depend on the intended range, field of view, lighting, deployment environment, host interfaces, weight, and budget.

#### 1. Core optical assembly — required baseline
- [ ] Camera / image sensor with a documented interface, supported capture path, and suitable resolution/frame rate.
- [ ] Compatible lens, focus adjustment, and optical mount; confirm field of view and working distance.
- [ ] Replaceable protective optical window, with glare/reflection and cleaning considerations.
- [ ] Rigid internal camera bracket, eye-like outer shell/bezel, fasteners, and alignment features.
- [ ] Camera cable and documented connector/pinout, with strain relief and service access.

#### 2. Capture, controller, and host interface
- [ ] Controller/interface board selected to support the camera and any chosen auxiliary sensors; do not assume a custom processor is necessary.
- [ ] Data transport selected after bandwidth, cable length, latency, and host compatibility are known (for example USB/UVC, CSI/MIPI with a compatible host/bridge, or Ethernet/GigE).
- [ ] Optional bridge/serializer-deserializer only when the chosen interface or cable run requires it.
- [ ] Bounded frame buffering and backpressure behavior; avoid unbounded queues.
- [ ] Timestamping and synchronization support. Use measured timestamps by default; add shared clock or hardware trigger only when multi-sensor synchronization requires it.
- [ ] Status/diagnostics access for connection, temperature, dropped frames, and module faults; service/programming access where applicable.

#### 3. Optional sensing — add only for a defined need
- [ ] Stereo camera pair or depth camera for depth/3D estimates when a single camera is insufficient.
- [ ] ToF/range sensor for independent distance evidence, chosen for the actual range, materials, and ambient-light conditions.
- [ ] IMU (accelerometer/gyroscope) if the optical head or wearer moves and orientation compensation is needed.
- [ ] Ambient-light sensor if exposure/illumination control needs it.
- [ ] Thermal/IR sensor only if thermal evidence is in scope and the chosen sensor supports the intended use.
- [ ] Microphone/audio, environmental sensors, or other modalities only when a specific use case justifies them.
- [ ] Every optional module needs a documented interface, power/data budget, calibration needs, provenance, and explicit health/failure reporting.

#### 4. Power and electrical protection
- [ ] Power input and connector matched to the actual deployment supply and measured worst-case load.
- [ ] Regulators/DC-DC conversion with appropriate voltage rails, current headroom, efficiency, and thermal rating.
- [ ] Overcurrent and reverse-polarity protection; ESD/surge protection where the interface/environment requires it.
- [ ] Accessible power switch/disconnect and correctly rated, labeled wiring harness.
- [ ] Optional voltage/current monitoring for power-budget verification.
- [ ] Grounding, EMI, cable routing, and thermal management checked against measured behavior.
- [ ] Battery and charging system only if portability requires them; use a compatible protected pack, appropriate charger, fuse/protection, and battery-specific safety plan.

#### 5. Mechanical package and wearable mounting
- [ ] Eye-like shell around the proven sensor stack; keep the cosmetic shell separate from the optical alignment structure.
- [ ] Internal frame, sensor brackets, spacers, service panels, and replaceable front bezel.
- [ ] Tripod, stand, wall, or platform adapter as appropriate; fixed mounting is the simpler baseline.
- [ ] Optional pan/tilt actuator and driver only if active aiming is required; include cable management and a safe end-stop strategy.
- [ ] Cable glands/strain relief and dust/moisture seals only to a defined, tested requirement.
- [ ] If using the wearable concept, padded adjustable behind-the-neck/shoulder harness, load-spreading supports, belt pouch, retention, ventilation, and safe cable routing. Fit-check with dummy weights before wearing powered electronics; do not obstruct the throat, head movement, or vision.

#### 6. Optional illumination
- [ ] Visible-light LED illuminator only if testing shows ambient light is insufficient.
- [ ] IR illuminator only with a compatible sensor/wavelength and a validated eye-safety plan.
- [ ] Driver, current control, diffuser/baffle, thermal path, and glare/reflection checks as required.
- [ ] Repeatable tests for low light, backlighting, glare, flicker, and lighting transitions before choosing an illuminator.

#### 7. Assembly and workshop equipment
- [ ] Precision screwdrivers, hex keys, tweezers, and non-marring tools.
- [ ] Wire cutters/strippers, suitable crimp tool and terminals, labels, heat-shrink, fasteners, and cable ties.
- [ ] Multimeter and current-limited bench supply for first power-up; USB power meter where useful.
- [ ] ESD-safe mat/wrist strap and suitable electronics-handling supplies.
- [ ] Soldering station and fume extraction only if selected modules require soldering; prefer connectorized parts where practical.
- [ ] Calipers/ruler and fit-check materials; 3D-printing or fabrication access only if a custom bracket/shell is needed.
- [ ] Appropriate electrical and optical safety equipment for the actual tools and illuminators used.

#### 8. Calibration and validation equipment
- [ ] Printed checkerboard/ChArUco target for camera intrinsics and lens-distortion calibration.
- [ ] Measured scale and known-distance targets for focus, field of view, and range checks.
- [ ] Stereo calibration target only if a stereo pair is selected.
- [ ] Known-distance reference setup and varied materials for depth/range error characterization.
- [ ] IMU calibration procedure/fixture only if an IMU is installed.
- [ ] Repeatable lighting scenes and a moving test object with a measured path.
- [ ] Logging/analysis host to record approved test frames, timestamps, sensor health, dropped frames, latency, temperature, power draw, and reconnect/recovery.
- [ ] Optional oscilloscope/logic analyzer only if bus timing, trigger synchronization, or electrical noise needs debugging.

#### 9. Software integration deliverables — not physical equipment
- [ ] Reproducible camera capture driver/configuration and a versioned hardware bill of materials (BOM).
- [ ] Interface/control documents, pinouts, voltage/current limits, bandwidth assumptions, and power budget.
- [ ] VIGIL sensor-provider adapter preserving timestamps, source provenance, coordinate frames, calibration metadata, and health state.
- [ ] Explicitly distinguish object not detected, blocked view, stale frames, disconnected sensor, provider failure, and object absence supported by evidence.
- [ ] Bounded queues, reconnect/recovery behavior, logging, and safe handling of partial sensor failure.
- [ ] Simulated/provider-level tests before committing to final hardware, followed by physical validation for every real-world performance claim.

#### 10. Modular acceptance checklist
- [ ] Camera-only baseline works without optional modules.
- [ ] Optional modules can be added/removed without redesigning the Coreless-64 machine or breaking the camera-only path.
- [ ] Connector pinouts, voltage/current limits, bandwidth, timestamps, units, coordinate frames, and calibration are documented.
- [ ] Module loss is reported as a module/provider fault and never silently treated as proof that an object is absent.
- [ ] Measure field of view, blind spots, focus/exposure, latency, dropped frames, power, temperature, and recovery.
- [ ] Claim depth, stereo, motion, thermal, or coverage performance only for modules actually installed and physically tested.
- [ ] Final enclosure fit, cable strain relief, serviceability, and operating temperature are checked.
- [ ] BOM records each part's role, required/optional status, compatible alternatives, interface, expected power draw, approximate cost, and sourcing/verification status.

#### Recommended build order
1. Define use conditions, target distance, field of view, lighting, environment, mounting, cable length, and budget.
2. Select a supported camera and lens, then prove capture on the intended host/interface.
3. Implement and test the VIGIL provider adapter with simulated observations.
4. Measure image quality, latency, power, and thermal behavior.
5. Add only optional depth/stereo/IMU/illumination/motion modules justified by the requirements.
6. Finalize the enclosure, harness, and wiring around the proven sensor stack.
7. Calibrate, fault-inject, and run physical acceptance tests; record verified part numbers and measured results in the BOM.

**Architecture boundary:** the VIGIL Eye is a physical sensor assembly. It feeds observations into VIGIL software; it is not the Coreless-64 software-defined machine, and it does not replace the machine's execution engine or spatial-intelligence software.

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
