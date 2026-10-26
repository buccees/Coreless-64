# Coreless Roadmap

**Side quests:** [Open the dedicated Side Quests page](SIDE_QUESTS.md) for optional experiments that should not displace core machine-development priorities.

## Immediate VIGIL priority queue — updated 2026-10-26

Work these items in order; keep existing priorities below this queue unless explicitly reordered.

1. **Underwater simulation → sonar sensor → terminal/game display.** Trace the existing simulation-to-sensor-to-terminal path first. Add simulated submerged contacts and underwater conditions, feed generated active/passive sonar observations through the existing authorized sensor pipeline, and display sensor state, estimated contacts/range, confidence, uncertainty, and stale status. Keep physical sonar hardware integration explicitly unverified until a real driver/data path is demonstrated.
2. **Fog of War player-isolation regression tests.** Verify that each player's contact picture and autonomous recon decisions use only that player's authorized observations; hidden truth remains evaluator-only.
3. **Preserve and extend the green autonomous-recon regression baseline.** Keep conflict follow-up, last-known-contact reacquisition, movement-aware uncertainty growth, and no-hidden-truth output assertions passing.
4. **Continue the existing VIGIL sensor-loop and multiplayer work** without claiming physical sensor connectivity or multiplayer transport until end-to-end checks prove it.

Underwater/sonar acceptance checks: simulated submerged contacts are not directly visible to players; active and passive sonar produce distinct observation behavior; missed/noisy detections and stale tracks are represented; sonar observations reach the terminal/game display through the sensor pipeline; player-isolation and Fog of War tests pass.

## Portability and hardware-identity goals

**The SSD holds the whole Coreless-64 machine, including its execution engine, OS/environment, configuration, and persistent state.** The OS runs on that machine. Lubuntu is the user's preferred OS for initial bring-up, not a host OS that owns Coreless execution. Keep the machine architecture, boot path, device model, and OS/runtime authority distinct from the chosen operating system. The portability goal is to boot and operate the Coreless machine from a broad range of supported SSDs and to expose Coreless's own identity through suitable hardware interfaces. The engineering goal is the complete SSD-carried machine, not a program installed on a host. Validate its execution/boot path and required physical interfaces against that architecture.

The portability goal includes USB-attached SATA/NVMe SSDs and native SATA/NVMe storage where the host firmware, bus, drivers, and boot path support them. Do not claim universal SSD compatibility without a tested drive/host/interface matrix.

Keep three concepts distinct: storage enclosure/controller identity, persistent Coreless machine identity, and optional hardware-level device identity exposed to another host. A normal external SSD cannot become a separate USB computer solely because Coreless software is stored on it. A distinct device-mode/composite interface requires compatible device-side controller hardware, firmware, transport implementation, and host-side validation; USB gadget/device mode is a hardware-dependent possibility, not a universal feature.

## Current checkpoint

The current implementation checkpoint includes the reference digital-machine lifecycle, persistent TensorRuntime, native vector/matrix execution foundations, Transformer → TensorRuntime routing, autonomous Coreless components, Hub composition, coordinated persistence, native CPU/VM component execution, Hub scheduling, a reference plug-and-play host transport layer, and an authenticated read-only Remote Operator Display endpoint backed by the active CorelessSystem. This operator surface reports runtime lifecycle and only those sensor events explicitly supplied to its telemetry provider; it does not imply physical sensor connectivity or a complete in-machine GUI.

## Development sequencing guardrail — 2026-10-23 (corrected project intent)

Coreless-64 is a **software-defined / virtual-hardware computer architecture**. The CPU, motherboard-level organization, memory, devices, execution engine, OS/runtime, AI capabilities, and connected components are modeled and implemented as project code and machine state; no physical Coreless motherboard or processor has been built. Do not describe modeled components as already-existing physical hardware, and do not redefine Coreless as an ordinary application whose intended computational owner is the host PC.

The removable SSD is intended to carry the complete Coreless machine image and persistent state. External equipment is only the physical substrate for power, storage connection, and negotiated I/O. The current bootable carrier is a transitional bootstrap: its Debian/Linux kernel and Python reference engine still execute on the CPU of the machine running the image. **A successful QEMU UEFI boot proves only that this bootstrap carrier builds, validates, and starts; it does not prove that the independent Coreless execution engine has replaced host-CPU execution or that the complete Coreless OS runs natively.** Keep this test as a useful packaging/bootstrap smoke test, but do not label it the native Coreless boot milestone.

Immediate task: finish the reproducible image build, offline image validation, and QEMU UEFI bootstrap test, accurately recording what passes. Then reconcile the carrier with the original architecture: load the persistent Coreless machine image, start the reference digital execution engine as the machine's executor, and validate the Coreless CPU/OS/runtime lifecycle within that machine boundary. Continue toward a boot chain that starts the Coreless machine rather than treating Linux as the final execution substrate. Do not discard the existing boot-test work; correct its scope and keep the native-engine integration as a required follow-on.

Remaining end-to-end work includes:
- Integrate the Coreless execution engine, machine boot, operating-environment startup, and persistent state as one verified lifecycle.
- Verify clean shutdown, restart, and persistence of both machine checkpoints and the VIGIL registry on the carrier state partition.
- Finish the VIGIL software integration and validate tracking, calibration, evidence/provenance, and operator-display behavior end to end.
- Implement concrete host/display/input/network transports and physical unplug/replug/reconnect on the first Lubuntu test host.
- Connect and validate real sensor providers; establish live spatial accuracy and coverage with measured calibration data.
- Validate local trained-model inference on Coreless resources and close the remaining native execution/model-part bindings.
- Perform physical SSD boot, power-cycle/reconnect persistence tests, and multi-host/storage compatibility testing.
- Complete the architecture/specification conformance audit and clearly distinguish automated tests from virtual and physical hardware validation.

## Phase 1 — Architecture

- [x] Coreless-64 architecture and independent-computer objective
- [x] CPU architectural state
- [x] Variable-length instruction encoding
- [x] Memory/address model
- [x] Privilege/interrupt architecture
- [x] Multiprocessing
- [x] Vector architecture
- [x] Matrix/AI architecture
- [x] Device/interconnect architecture
- [x] Autonomous component/hub architecture
- [x] Plug-and-play host boundary specification
- [x] Graphics/display architecture
- [x] Virtualization architecture
- [ ] Final specification consistency audit and normative v1.0 freeze

## Phase 2 — Digital execution engine

- [x] ISA decoder/instruction-length engine
- [x] CPU execution core
- [x] Memory system
- [x] Interrupt/timer foundation
- [x] Atomic execution
- [x] Persistent machine state
- [x] Storage-backed virtual RAM
- [x] Shared RAM across CPUs
- [x] Persistent CPU state
- [x] Network controller reference model
- [x] Virtual GPU/display model
- [x] Vector execution
- [x] Matrix/AI execution
- [x] Multiprocessing fabric
- [x] Virtualization model

## Phase 3 — Coreless operating environment

- [x] Firmware
- [x] Boot
- [x] Reference Coreless OS runtime
- [x] Process model
- [x] Memory management
- [ ] Device drivers
- [ ] Networking
- [ ] GUI
- [x] Authenticated read-only remote operator display page and runtime-state endpoint (reference implementation)
- [ ] Complete in-machine GUI and platform-specific display/input transports
- [x] User-designated pointing-device subsystem
- [x] Touch/pointing input routing through Coreless input boundary
- [x] Initial optional VIGIL input interpretation layer
- [x] Plug-and-play host discovery and identity handshake software contract
- [x] Host capability negotiation and attach/detach software contract
- [x] Reference host enumeration/transport adapter
- [x] Provider-backed host transport adapter boundary
- [x] Transport-neutral host hot-plug lifecycle coordinator (software contract only)
- [x] Optional Linux udev event source with immutable, allowlisted OS-event snapshots and injected lifecycle tests (`reference/linux_udev_events.py`)
- [x] Integrate Linux udev lifecycle events with `HostHotplugController` through a resolver boundary and fresh-snapshot identity validation (`reference/linux_host_hotplug.py`; physical transport close/reopen remains open)
- [ ] Implement concrete Linux transport close/reopen and validate physical unplug/replug and reconnect on the first Lubuntu test host
- [ ] End-to-end VIGIL integration with native hot-plug lifecycle
- [ ] Application environment

## Phase 4 — Complete digital machine

- [x] Persistent process/address-space state
- [x] Persistent OS/device/boot/application state
- [x] Checkpoint/restore
- [x] Coordinated Hub checkpoint commit verification and failed-commit manifest rollback
- [x] Resume from machine image
- [x] Complete reference lifecycle through the digital execution engine
- [x] Autonomous component execution boundary
- [x] Hub workload routing and parallel dispatch
- [x] Native CPU/VM execution for component VMs
- [x] Hub multi-vCPU scheduling

## Phase 5 — Portable Coreless machine

- [ ] Validate the Coreless execution engine → machine boot → operating-system startup path as one integrated lifecycle
- [ ] Prepare a dedicated, disposable portable SSD for the first physical bring-up; record SSD/controller, connection type, firmware/boot settings, and target-computer details before writing anything
- [ ] Install the complete Coreless machine image on that SSD and verify the actual boot chain rather than treating a repository checkout or file copy as an installed machine
- [ ] Run a first-host boot/OS/runtime acceptance test and confirm the OS executes within the Coreless machine boundary
- [ ] Power down, disconnect/reconnect the SSD, and verify machine identity and persistent state survive; then repeat on a second compatible host
- [ ] Record a tested SSD/controller/host/firmware compatibility matrix; do not claim broad portability from a single successful setup
- [ ] Define and validate the boot contract so the OS runs on the Coreless execution engine and retains machine-level authority

- [ ] Define a storage compatibility matrix (USB-attached SATA SSD, USB-attached NVMe SSD, native SATA, native NVMe; include boot firmware/driver constraints)
- [ ] Test persistent Coreless machine portability across multiple SSDs and host computers without assuming storage identity equals Coreless machine identity
- [ ] Specify hardware-level Coreless device identity separately from storage/enclosure identity
- [ ] Evaluate distinct USB/device-mode enumeration on compatible hardware; document required controller/firmware and test host interoperability before claiming support

- [x] Reproducible digital/reference test environment
- [x] Complete reference machine lifecycle
- [x] Persistent TensorRuntime
- [x] Transformer execution through TensorRuntime
- [x] Stable native Coreless execution boundary for Transformer tensor operations
- [x] TensorRuntime RMSNorm, scalar broadcast, and transpose primitives
- [x] Qwen3 rotary/masking/scalar-scale/argmax paths routed through TensorRuntime
- [x] TensorRuntime-backed Qwen3 KV-cache storage and native head reshape/repeat/data-movement boundary
- [x] Actual persistent-storage-hosted Coreless runtime environment
- [ ] Live five-core inference on Coreless
- [ ] End-to-end local AI execution on Coreless resources

## Static-Adaptive Model Parts

- [x] ModelPart lifecycle/task contract
- [x] Candidate → validating → active → retired lifecycle
- [x] Validation before replacement
- [ ] Architecture-specific native execution for Qwen3, DeepSeek/R1, gpt-oss, Gemma, Codestral
- [ ] Model-part ABI/VM IPC/capability integration
- [ ] Specialization planner
- [ ] User/workload adaptation state
- [ ] Slimming/pruning/quantization
- [ ] Regression/acceptance suite
- [ ] Adaptation history/rollback
- [ ] Continuous workload adaptation triggers

## AI-Derived Hardware Components

- [x] Storage-backed safetensors
- [x] Native Qwen3 artifact validation/loading
- [x] Native Qwen3 tokenizer/greedy generation
- [x] Qwen3 KV cache generation/layout
- [x] Qwen3 grouped-query attention cache layout and generation path
- [x] Real artifact integration runner
- [ ] Official trained Qwen3-0.6B end-to-end validation
- [x] CPU/GPU/communication capability envelopes
- [x] Explicit hardware-role assignment
- [x] Native architecture preservation
- [x] Model-part execution endpoints and fabric routing
- [ ] Bind CPU model part to Coreless-64 instruction execution
- [ ] Bind GPU model part to graphics/device/driver execution
- [ ] Bind communication model part to user session layer
- [ ] Native architecture adapters
- [ ] Live trained model components

## 314DNest / Local Intelligence

- [x] AI-Core registry
- [x] Multi-model coordination
- [x] Deterministic group result
- [x] Dynamic workload distribution/failover
- [x] Deterministic policy boundary
- [x] Capability-controlled Coreless resources
- [x] Telemetry/audit
- [x] Human-AI sessions
- [x] Structured terminal ABI
- [x] Cancellation/bounded workers
- [x] Optional OpenAI adapter
- [x] Local model runtime adapters
- [x] Native AI compute resource/scheduler
- [x] Unified machine work-distribution API
- [x] Digital/reference test environment
- [x] Local TensorRuntime foundation
- [x] Transformer execution foundation
- [x] Model-format/loading foundation
- [x] Native Coreless execution boundary
- [ ] Live five-core inference
- [ ] End-to-end local AI on Coreless resources

## Phase 6 — Scaling

- [ ] Dynamic CPU/memory/vector/AI/GPU scaling
- [ ] Large persistent machine images
- [ ] Multiple guest machines
- [ ] Multi-device Coreless systems
- [ ] Autonomous component hot-plug across Coreless Hubs

## Phase 7 — Compatibility

- [ ] Coreless-native toolchain
- [ ] x86-64 compatibility
- [ ] ARM64 compatibility
- [ ] Guest operating systems
- [ ] Binary translation
- [ ] Legacy virtualization

## Plug-and-play host interface

- [x] Host boundary defined as external I/O, not Coreless computation
- [x] Identity/discovery requirements documented
- [x] Capability negotiation requirements documented
- [x] Component/hub composition boundary documented
- [x] CorelessHostInterface software contract
- [x] Reference host enumeration/transport adapter
- [ ] Validate physical host enumeration on Lubuntu/Linux, then add tested providers for other supported host OSes
- [x] Reference display/input/network transport adapters
- [ ] Validate display/input/network transport adapters on Lubuntu/Linux, then add other OS adapters
- [x] User-designated pointing-device discovery and persistent assignment
- [x] Coreless touch/pointing event transport contract
- [x] VIGIL-aware input interpretation boundary
- [x] Input-device failover and reassignment

## VIGIL input integration

The Coreless input architecture uses VIGIL as an optional interpretation layer. VIGIL is now contained in the Coreless repository rather than being a separate runtime dependency.

- [x] Define Coreless input event ABI for pointer, touch, stylus, and gesture events
- [x] Define user designation and persistent identity for a primary pointing device
- [x] Define device discovery, capability advertisement, assignment, reassignment, and failover
- [x] Route designated pointing-device events through the Coreless input boundary
- [x] Define initial VIGIL interpretation API and capability boundary
- [ ] Implement gesture and multi-touch interpretation through VIGIL
- [x] Preserve raw-event access for applications that do not use VIGIL
- [x] Keep VIGIL optional so basic pointer/touch operation does not depend on VIGIL
- [x] Add deterministic input regression/acceptance tests
- [x] Integrate VIGIL input state with persistent Coreless machine state where appropriate
- [x] Add optional camera-frame ingestion boundary
- [ ] Implement camera perception/tracking
- [ ] Implement camera-based pointing
- [ ] Implement spatial gesture recognition
- [ ] Implement VIGIL spatial/world-model services inside Coreless

## Current blocker — VIGIL hot-plug unavailable

VIGIL **cannot use hot-plug yet**. The transport-neutral `HostHotplugController` has software lifecycle tests, and `reference/linux_udev_events.py` now provides an optional pyudev event source with unit-tested snapshot and observer lifecycle behavior. That source only reports OS device events: it does not verify Coreless identity, attach endpoints, close/reopen transports, or prove physical unplug/replug. Those integration and hardware checks, plus an end-to-end VIGIL test, remain incomplete. Do not describe VIGIL hot-plug as available until those checkpoints pass. VIGIL spatial-intelligence work is active again.

## Resume point

**Current next priorities:** implement and validate concrete platform host enumeration and display/input/network transport adapters; validate the existing authenticated Remote Operator Display against the active machine lifecycle and observed VIGIL event ledger without fabricating sensor state; then continue deeper native Coreless execution and official trained Qwen3-0.6B end-to-end validation. The VIGIL spatial-intelligence work is active again; preserve the existing research notes and historical decisions.


## Latest transport milestone

The reference plug-and-play boundary now includes reusable transport sessions above identity and command framing.

- [x] Transport-neutral Coreless identity frame
- [x] Correlated device command/response frame
- [x] Reference host endpoint enumeration
- [x] Capability negotiation and channel binding
- [x] Reusable host transport session
- [x] Session command exchange and correlated responses
- [x] Session close preserving Coreless machine state
- [ ] Cross-platform physical host enumeration
- [ ] Concrete display/input/network transport adapters


## Documentation checkpoint — 2026-10-06: scheduler and dispatch throughput

The latest documented scheduler milestone was GitHub Actions **#1124**, commit `5df0639e70e4c7ada1143146d5121ec2731e93f5`. The current verified green repository checkpoint is GitHub Actions **#1244**, commit `674ea90b251fdad141b338be880b644b21d89113`. The preceding scheduler snapshot implementation exposed one incorrect empty-scheduler test expectation; that test was corrected to register a real resource and verify the scheduler-owned `(capacity, load)` snapshot. The implementation was unchanged by that correction.

The current throughput architecture now includes:

- scheduler-owned atomic resource state snapshots;
- eligible-capacity snapshots that preserve operation capability and AI model-affinity filtering;
- worker sizing from actual eligible capacity rather than total registered capacity;
- unified capacity accounting across parallel dispatch paths;
- direct single-item scheduler dispatch without thread-pool setup;
- deque-backed pending-work queues for constant-time admission;
- telemetry consumption from consistent scheduler resource state;
- preserved allocation, fallback, result-ordering, persistence, and AI authorization contracts.

This is an optimization layer over the existing Coreless machine architecture, not a change in computational authority. The scheduler remains the owner of resource allocation; AI remains a local machine resource and never becomes an authorization mechanism.

### Throughput architecture milestone

- [x] Scheduler-owned atomic resource state snapshots
- [x] Eligible-capacity dispatch accounting
- [x] AI model-affinity-aware concurrency sizing
- [x] Single-item scheduler fast path
- [x] Deque-backed pending dispatch queue
- [x] Unified scheduler capacity accounting
- [x] Telemetry/resource-state hot-path optimization


## Documentation checkpoint — 2026-10-07: Qwen3 tensor boundary verified

The existing implementation provides the Qwen3 KV-cache/head-data **software boundary** through TensorRuntime-backed append/persistence, head reshape/repeat, grouped attention, and focused regression coverage. Code reviewed on 2026-10-22 in `ai/qwen3.py`, `ai/tensor_runtime.py`, `ai/test_qwen3.py`, and `ai/test_tensor_runtime.py` confirms this checklist item is complete; do not reopen it as missing implementation. Scope limit: Tensor payloads still use Python numeric tuples, and several runtime operations execute Python-level loops/fallbacks, so this is not proof of hardware-native data movement or trained-model end-to-end inference. Open checkpoints remain: deeper native Coreless execution and performance validation, concrete host transport adapters, and official trained Qwen3-0.6B end-to-end validation.


## Documentation checkpoint — 2026-10-07: persistent runtime launcher

The persistent-storage-hosted reference runtime now has a direct launcher at `scripts/coreless-run.py`. It opens the Coreless machine image as the authoritative state carrier, resumes the Coreless OS/runtime, accepts native Coreless shell commands, optionally advances the digital execution engine, and persists shutdown/state without moving computational authority into the host. Lifecycle regression coverage is in `reference/test_persistent_runtime.py`.


## Documentation checkpoint — 2026-10-07: reference host I/O integration

The host transport milestone has advanced from negotiated channels to an end-to-end reference I/O path. The Coreless host boundary can now bind a persistent Coreless system to concrete in-memory display, input, and network transports. Input events are serialized into the host channel and decoded back into the Coreless input ABI; display scanout frames can be emitted to the host display transport; and network packets can cross the host boundary in both directions.

Verified CI runs include #1314 (end-to-end host I/O integration) and #1315 (clean host I/O reconnect handling), both green. The remaining host-interface work is platform-specific enumeration and transport adapters.


## Documentation checkpoint — 2026-10-07: platform-independent host discovery

The reference host boundary now has a dedicated platform-independent discovery layer in `reference/host_discovery.py`. `HostDeviceEnumerator` accepts raw transport-neutral identity advertisements from concrete adapters, validates Coreless-64 identity/protocol data, derives device capabilities from the advertisement, and returns deterministically ordered `HostEndpoint` objects. Duplicate endpoint IDs and malformed identity frames are rejected before attachment.

This separates transport-neutral Coreless discovery from future OS/device-specific enumeration. Physical USB, PCIe, Ethernet, SATA, NVMe, display, input, and network adapters remain outside this layer and must continue to use the same discovery contract.


## Documentation checkpoint — 2026-10-07: HostIO transport boundary

The host transport layer now validates the transport-neutral HostIO bundle before endpoint attachment, and HostTransportAdapter.open_session() carries the same explicit HostIO contract. Invalid host I/O bundles are rejected before Coreless attachment state changes. This completes the reference software boundary for negotiated display/input/network I/O; physical OS/device enumeration and platform-specific transport adapters remain intentionally separate implementation work.

- [x] Transport-neutral HostIO channel contracts
- [x] Transport-neutral HostIO bundle contract
- [x] HostIO bundle validation at the Coreless boundary
- [x] HostIO bundle validation at the transport connection boundary
- [x] HostIO-aware reusable transport sessions
- [ ] Cross-platform physical host enumeration
- [ ] Platform display/input/network transport adapters


## Documentation checkpoint — 2026-10-07: atomic HostIO validation

- [x] Validate the complete negotiated HostIO bundle before attachment
- [x] Validate the Coreless input-router contract before binding
- [x] Preserve no-partial-attachment behavior on HostIO validation failure

The reference test suite is green at this checkpoint. Next implementation work should proceed toward concrete platform host providers/adapters while preserving the transport-neutral boundary.

## Documentation checkpoint — 2026-10-23: VIGIL spatial work active

Spatial-intelligence development is active again. Added `vigil/spatial_query.py` and focused regression tests. The query engine reports nearest modeled feature, distance, level/zone labels, and optional nearby features only after checking model/revision/frame identity, pose timestamp, freshness, tracking state, and uncertainty. It distinguishes missing fix, stale data, future timestamps, mismatched model/frame, and degraded-but-usable estimates.

This completes the first deterministic spatial-query API slice; it does not claim polygon-region semantics, raw CAD/PDF import, live sensor discovery, or physical tracking accuracy. Query results, explicit model-frame regions, persistent blueprint/region/calibration metadata, and the authenticated operator overlay are implemented. Continue toward a complete spatial workflow with deterministic sensor replay, connected raster/sensor-mount calibration, concrete live adapters, and physical field validation. Keep hardware accuracy claims separate from software CI.

### VIGIL spatial query and region milestone — 2026-10-23

- [x] Confidence-aware nearest-feature query API with freshness, frame/revision, and uncertainty gates (`vigil/spatial_query.py`)
- [x] Explicit model-frame polygon regions with vertical bounds and safe membership results (`vigil/spatial_regions.py`)
- [x] Regression coverage for missing/stale/future/mismatched poses, degraded estimates, region boundaries, and invalid geometry
- [x] Connect query/region results to workspace snapshots, terminal status, and authenticated browser spatial overlay
- [x] Reject self-intersecting/degenerate polygons and canonicalize closed polygon rings
- [ ] Add a reviewed region-import/editor workflow for user-drawn or imported regions
- [x] Persist normalized model revisions, regions, calibration metadata, and active-model pointer in the SQLite spatial registry
- [x] Persist exact imported JSON source-manifest bytes as checksummed immutable assets tied to the normalized model revision
- [x] Add deterministic checksummed portable registry bundle export/restore for model revisions, regions, raster calibrations, sensor mounts, source assets, tracks/history, and active-model pointer
- [ ] Integrate registry bundle export/restore into the final Coreless OS/SSD snapshot, boot, and copy lifecycle
- [ ] Add end-to-end deterministic sensor replay across pose, object tracks, scene assembly, and region alerts
- [ ] Implement and validate concrete sensor drivers; do not claim field accuracy from simulation/CI

### VIGIL spatial persistence — 2026-10-23

- [x] SQLite spatial registry for immutable model revisions, explicit regions, and raster calibration metadata
- [x] Canonical JSON integrity checks and per-record size limits
- [x] Restore active model and regions into a fresh `SpatialWorkspace`
- [x] Persist bounded last-known object-track evidence/history and restore tracks as `REACQUIRE` after restart
- [x] End-to-end restart coverage for model/region persistence and explicit revision activation
- [x] Persist source manifests and sensor-mount transform/calibration provenance in the VIGIL registry
- [x] Open the persistent VIGIL registry from the bootable carrier console and restore the active model, lifecycle history, and alert acknowledgements at startup (SQLite remains a separate carrier-owned registry, not yet unified with the Coreless storage service)\n- [ ] Integrate all VIGIL registry data and arbitrary source assets with the full Coreless storage service
- [x] Connect saved raster calibrations to timestamped IR pixel ingestion and saved sensor-mount transform application
- [ ] Complete raw image decoding adapters and survey-driven sensor-mount calibration

### VIGIL authenticated spatial operator overlay — 2026-10-23

- [x] Versioned JSON spatial snapshot contract with model bounds, selected level, pose freshness, features, tracks/trails, region results, uncertainty, and provenance
- [x] Authenticated read-only `GET /api/vigil/spatial` endpoint; no browser-supplied model state or commands
- [x] Live SVG plan overlay in `operator-display.html`: modeled features, region polygons/membership, pose, object locations/trails, state and sensor details
- [x] Explicit current / stale-last-known / conflict / no-fix displays, with stale objects excluded from current-evidence readiness
- [x] CLI integration supports a persistent spatial registry beside the machine image and optional versioned JSON blueprint import (`--spatial-db`, `--blueprint`)
- [ ] End-to-end validation on a real hosted HTTPS instance and actual calibrated sensor feeds
- [ ] Physical sensing accuracy, coverage limits, false-positive rates, and device-loss/reacquisition validation


### Current spatial engineering checkpoint — 2026-10-23

- [x] Object evidence/provenance, sensor independence groups, calibration IDs/status, and lineage declaration visible in the authenticated snapshot and operator cards.
- [x] Provider health exposed as `UNPOLLED`, `ONLINE`, or `ERROR`; failing providers do not block healthy providers.
- [x] Persist bounded track history/evidence and restore as `REACQUIRE`, never as live contact.
- [x] Align live spatial snapshot and test-fixture timestamps to monotonic nanoseconds.
- [x] Confirmed green endpoint-fixture workflow: [40005690022](https://github.com/buccees/Coreless-64/actions/runs/40005690022). The implementation-only run [40005685759](https://github.com/buccees/Coreless-64/actions/runs/40005685759) failed on its then-old fixture; the subsequent fixture commit is green.
- [ ] Verify CI after the current documentation updates.
- [ ] Add deterministic sensor replay for pose, object tracks, scene assembly, and region alerts.
- [x] Connect saved raster calibrations to timestamped IR pixel-batch ingestion with active model/revision/frame checks
- [x] Add persisted rigid sensor-mount transforms and an explicit sensor-local observation ingestion path with frame/sensor/revision checks
- [ ] Measure/validate transform values against actual mounted hardware; software validation does not establish physical accuracy
- [ ] Validate live drivers, coverage/false positives, ranging quality, and reacquisition on actual hardware.

Spatial development remains active. Software CI is not field-validation evidence.


## Side quest — VIGIL Eye: modular optical sensor head

Tracking issue: [#22 — Side quest: VIGIL Eye — modular optical sensor head](https://github.com/buccees/Coreless-64/issues/22)

The VIGIL Eye is an optional, replaceable physical optical module inspired by the single-eye silhouette in *Alien: Earth*. It should feed real sensor evidence into VIGIL's existing spatial-awareness pipeline; it is not a substitute for the Coreless-64 machine, its execution engine, or spatial intelligence.

- [ ] Define a practical first-prototype camera and power/data interface
- [ ] Compare camera-only, stereo, and depth-camera approaches for object localization
- [ ] Specify mount, field of view, lighting, calibration, timestamps, coordinate frame, provenance, and provider-health reporting
- [ ] Integrate a simulated sensor provider before hardware selection
- [ ] Prototype with real hardware and measure latency, coverage, range accuracy, blind spots, and reacquisition
- [ ] Design the eye-like enclosure around validated sensor, power, and thermal requirements
- [ ] Document limits: one eye sees only its available field of view; broader awareness requires additional evidence sources

This is a side quest. It must not silently displace the current boot/host-I/O/runtime validation priorities. Software tests and simulation are not evidence of physical sensing accuracy.


### VIGIL sensor-health acknowledgement milestone — 2026-10-23

- [x] Persist integrity-checked sensor-alert acknowledgements in SQLite.
- [x] Expose acknowledgement state and UTC/operator metadata in the spatial snapshot.
- [x] Add an authenticated, same-origin POST endpoint that only acknowledges currently active alerts.
- [x] Add operator-display acknowledgement controls and explicit failure feedback.
- [x] Clear acknowledgements when a subsequent snapshot observes that the incident has recovered, allowing a later observed recurrence to require acknowledgement again.
- [ ] Confirm the full regression and bootable-carrier workflows pass for this milestone.
- [ ] Validate the acknowledgement workflow on the deployed authenticated HTTPS operator display.


### Carrier startup ↔ VIGIL persistence integration — 2026-10-23

- [x] Initialize the VIGIL spatial registry from the carrier's persistent state directory during machine-console startup.
- [x] Add a dedicated `CORELESS_STATE` GPT/ext4 partition mounted at `/var/lib/coreless`, keeping the machine image and VIGIL registry independent from the bootstrap root filesystem.
- [x] Restore active model/revision, regions, expected sensor coverage, last-known tracks, lifecycle history, and alert acknowledgements through the existing workspace/store restoration paths.
- [x] Add the `:spatial` console command to inspect restored model and persisted sensor/alert history counts.
- [x] Add a restart integration test for active model, sensor lifecycle history, alert acknowledgement restoration, and last-known object-track evidence restored as `REACQUIRE`.
- [ ] Verify the new commit's complete CI suite and bootable-carrier image workflow.
- [ ] Validate state-partition formatting/mounting by building and booting the revised three-partition image.
- [ ] Exercise a physical SSD reboot and confirm the registry survives power-off/reconnect on the target host.
