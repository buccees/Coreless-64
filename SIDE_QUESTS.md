# Side Quests

Optional explorations that complement Coreless-64 and VIGIL without silently displacing the main machine-development priorities.

## VIGIL Eye — modular optical sensor head

**Status:** Captured; design and prototyping not yet started.

**Tracking issue:** [#22 — Side quest: VIGIL Eye — modular optical sensor head](https://github.com/buccees/Coreless-64/issues/22)

### Concept

A replaceable, eye-like optical module inspired by the single-eye silhouette in *Alien: Earth*. The module provides real visual sensor evidence to VIGIL's spatial-awareness system; it is not the Coreless-64 machine or the spatial intelligence itself.

### Planned work

- [ ] Define a practical first-prototype camera and power/data interface.
- [ ] Compare camera-only, stereo, and depth-camera approaches for object localization.
- [ ] Specify mount, field of view, lighting, calibration, timestamps, coordinate frame, provenance, and provider-health reporting.
- [ ] Integrate a simulated sensor provider before hardware selection.
- [ ] Prototype with real hardware and measure latency, coverage, range accuracy, blind spots, and reacquisition.
- [ ] Design the eye-like enclosure around validated sensor, power, and thermal requirements.

### Acceptance criteria

- Observations enter VIGIL through a documented provider interface with timestamps and provenance.
- Calibration and sensor pose are explicit; estimates are not represented as ground truth.
- Loss of view/provider failure is distinguishable from evidence that an object is absent.
- The optical head can be replaced without redesigning the Coreless-64 machine.
- Accuracy and coverage claims are backed by physical tests, not only simulation or CI.

### Constraints

A single camera only sees its available field of view. Broader awareness requires additional sensors or other evidence sources. Keep this side quest from displacing the main boot, host-I/O, and runtime-validation work.
