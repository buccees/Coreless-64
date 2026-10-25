# Coreless-64 — Project Handoff

## Portability and hardware-identity goals

## Permanent machine boundary — monitor and I/O only

**The Coreless-64 machine is self-contained on the SSD, including its execution engine and operating system. To use the machine, the outside world should need only a monitor/display and input/output (I/O) connections.** External equipment is an interface, not the source of Coreless computation or architectural authority. Do not design around a separate host computer supplying the CPU, RAM, OS execution, AI computation, or runtime. Treat display and I/O transport adapters as the external boundary; any physical implementation must still be validated against its actual hardware.

**The SSD holds the whole Coreless-64 machine—not merely its files or saved state.** The complete machine includes its execution engine, OS/environment, configuration, and persistent state; the OS runs on that machine. Lubuntu is the user's preferred OS, not a host OS that owns or executes Coreless as an application. Keep machine architecture and OS/runtime authority independent from the chosen OS. Design storage and external interfaces for broad compatibility; use Lubuntu as the first bring-up/validation environment, not as the machine's architectural boundary. Target broad SSD compatibility (USB-attached SATA/NVMe and native SATA/NVMe where firmware and drivers permit), but do not promise every drive/host combination without a compatibility matrix and tests.

The user wants Coreless to register as a distinct piece of hardware, not merely be seen as files on an SSD. The SSD-carried machine includes its execution engine; the OS runs on that engine. The repository already contains a digital reference execution engine. Do not reframe the engine as a missing future feature or describe the SSD as only storage. Remaining work is to validate the integrated machine boot/OS path and implement the required physical host/device interfaces for the chosen deployment. Keep three identities separate: (1) the storage device/enclosure identity exposed by its controller, (2) the Coreless machine identity carried by persistent state/protocol, and (3) any optional physical device-mode identity exposed to another host. Software on an ordinary SSD cannot make its enclosure enumerate as a separate computer by itself; that requires compatible device-side hardware/firmware and an implemented transport. Treat USB gadget/device mode as a hardware-dependent option, not a universal assumption.

For native hot-plug, `reference/linux_udev_events.py` provides an optional pyudev event source with allowlisted immutable event snapshots, and `reference/linux_host_hotplug.py` now wires lifecycle events through a resolver boundary into `HostHotplugController`. The controller re-enumerates a fresh endpoint snapshot and the provider-backed adapter validates the advertised Coreless identity before attachment. Unit tests cover arrival/removal, missed-event reconciliation, unknown devices, stale discovery, and callback failures. This is still not physical end-to-end hot-plug: a concrete transport resolver and safe transport close/reopen must be validated on Lubuntu, followed by physical unplug/replug and VIGIL integration tests.

## First physical portable-SSD validation

The first hardware proof must use a dedicated, disposable portable SSD. Before writing to it, record the drive/controller, connection type (USB-attached SATA/NVMe or native SATA/NVMe), target machine, firmware/boot settings, and recovery plan. Install the complete Coreless machine image only after the boot contract is defined; a repository checkout or copied files alone do not prove that the SSD carries a bootable, self-contained machine. Validate the engine-to-boot-to-OS/runtime lifecycle on the first Lubuntu bring-up host, then perform safe shutdown/reconnect checks for persistent machine identity and state, and repeat on a second compatible host. Preserve the existing data on any user drive; do not assume a target SSD can be overwritten without explicit selection and backup. Record exact successful and failed drive/host/firmware combinations in a compatibility matrix. A successful storage boot does not by itself prove that the SSD enumerates as a separate USB computer; that requires suitable device-side hardware and a separate interface test.

## Current blocker — VIGIL cannot use host hot-plug yet

**Do not treat hot-plug as available to VIGIL right now.** The repository has a transport-neutral `HostHotplugController` for validated arrival, removal, and missed-event reconciliation, plus an optional Linux udev event source with unit-tested event snapshots and observer lifecycle. The udev source alone does not identify Coreless endpoints. The new adapter connects event handling to the controller but still depends on a real platform resolver/transport provider; physical unplug/replug and reconnect validation and end-to-end VIGIL integration remain incomplete. Consequently, VIGIL cannot rely on automatic physical device arrival/removal or reconnect behavior yet.

Next required hot-plug work: implement the concrete Linux identity resolver and transport close/reopen, then verify unplug/replug and failure recovery on the first Lubuntu test host. Separately, define and test a storage/host compatibility matrix and specify what physical interface can expose Coreless as a distinct device. Add an end-to-end VIGIL integration test before marking this usable. Keep the VIGIL spatial-intelligence expansion paused; this note records a blocker, not permission to resume that work.

## Current state

**Status: green.** The repository is at a stable checkpoint with the Coreless-64 digital machine foundation, 314DNest control plane, persistent tensor runtime, Transformer integration, autonomous component execution, Hub scheduling, and reference host transport layer all passing CI.

The project has two connected layers:

1. **Coreless-64** — the 64-bit digital computer architecture and execution engine.
2. **314DNest** — the local System Fabric that coordinates AI cores with Coreless resources through deterministic interfaces and policy.

314DNest is not the Coreless CPU and is not a remote AI dependency. CPU, MMU, hypervisor, and architectural protection remain authoritative.

## Autonomous component architecture

Coreless now explicitly treats **autonomous, specialized, composable components** as a first-class architectural requirement.

A component is intended to be a complete Coreless computer unit, not merely a peripheral. Its integrated boundary includes:

- Coreless execution
- local memory/storage
- VM isolation
- local AI runtime/model
- role specialization
- persistent identity
- capability advertisement
- component communication/discovery
- health and fault isolation

A component must be able to operate independently.

A Coreless Hub is the composition boundary. It discovers components, records their identities and capabilities, connects/disconnects them, and aggregates their capabilities into a unified composition.

The intended lifecycle is:

**component → standalone operation**

and:

**component A + component B + component C → Coreless Hub → unified Coreless computer**

Connecting components does not turn them into passive peripherals. Each component retains its own identity, specialization, AI, VM, and execution boundary.

Per-component AI is intentional. A component can carry a role-specific model and use its VM as the controlled environment for training, adaptation, evaluation, and model updates. AI remains subject to deterministic Coreless CPU, VM, capability, and policy controls.

The first software boundary is now implemented in:

- `reference/components.py`
- `reference/test_components.py`
- `specification/component_architecture.md`

This layer establishes identity, specialization, standalone state, hub discovery, connect/disconnect, capability composition, fault isolation, and deterministic workload dispatch.

## Coreless-64 completed foundation

- 64-bit architectural model
- variable-length 32/64/128-bit instruction framing
- scalar, memory, branch/jump, system, atomic, vector, matrix, crypto, and VM instruction families
- USER, SUPERVISOR, HYPERVISOR, and MACHINE privilege levels
- precise traps and retirement behavior
- CSR privilege/read-only enforcement
- R0 hard-wired to zero
- MMU/TLB permission foundations
- interrupts and traps
- vector and matrix architectural state
- multiprocessing foundations
- persistent machine storage
- storage-backed virtual RAM
- graphics/display and networking foundations
- VM isolation and hypervisor lifecycle/state control
- directional VM IPC
- cross-VM shared-memory capabilities
- VM capability revocation on destruction
- conformance tests and green CI baseline

## Coreless system lifecycle

The reference machine now has a complete digital lifecycle layer through `reference/system.py`.

`CorelessSystem` provides:

- persistent boot manifest
- boot
- run
- native Coreless shell command routing
- checkpoint
- restore
- shutdown
- persistent machine status/state handling

The reference OS/process/memory-management lifecycle is represented in the repository and covered by tests.

## 314DNest completed foundation

Completed:

- AI-Core registry
- concurrent multi-model coordination
- deterministic collaboration and group results
- disagreement handling without automatic selection
- dynamic workload distribution
- failover/reassignment
- bounded worker scheduling
- cancellation
- deterministic policy boundary
- explicit capability enforcement
- direct binding to Coreless CPU/memory/storage/device controls
- Coreless hypervisor VM start/stop control
- telemetry provider
- append-only audit log
- human-AI session layer
- structured terminal command ABI
- confirmation handling for sensitive terminal commands
- optional OpenAI development adapter

Current local AI participants include Qwen3, DeepSeek, gpt-oss, Gemma, and Codestral. GPT-5.6 Luna remains optional through the OpenAI adapter.

### Security/control rule

**AI output is never authorization.**

Protected flow:

**AI result → structured proposal → deterministic policy → capability check → Coreless resource → telemetry/audit**

Natural-language approval, model identity, VM identity, or storage location cannot substitute for an explicit capability.

## Tensor runtime — current checkpoint

The persistent tensor runtime is now bound to the Coreless machine and its vector/matrix execution foundation.

Relevant files:

- `ai/tensor.py`
- `ai/tensor_runtime.py`
- `reference/core.py`
- `reference/machine_runtime.py`

Implemented:

- dtype-aware tensor creation
- fp16/bf16/fp32/fp64 and int8/int16/int32/int64 semantic dtypes
- persistent tensor state
- Coreless CPU binding
- native vector add
- native vector multiply
- deterministic vector dot using native vector multiplication plus deterministic reduction
- native integer matrix multiplication for supported architectural shapes
- automatic routing of supported integer matrix multiplication through the Coreless matrix unit
- generic fallback for unsupported shapes/dtypes
- FP32 vector execution coverage
- tensor persistence across machine reopen
- TensorRuntime scalar broadcast and transpose primitives
- Coreless-native RMSNorm, reciprocal/rsqrt, rotary trig, masking, scalar scaling, and deterministic argmax paths
- Qwen3 regression boundaries proving model operations cross the TensorRuntime API

Important limitation: the current Tensor object still stores values as Python numeric tuples while dtype remains a semantic/storage label at the runtime boundary. Do not describe this as true hardware-format storage yet.

## Transformer integration — current checkpoint

Transformer execution is now routed through the persistent Coreless tensor runtime.

Implemented:

- dtype-preserving embedding
- RMS normalization
- scaled dot-product attention through the runtime when supplied
- feed-forward matrix operations through the runtime
- Transformer-layer residual and matrix operations through the runtime
- final language-model head routing through the runtime
- explicit regression test proving matrix multiplication calls cross the TensorRuntime boundary

The documented green checkpoint for the latest control-flow conformance batch is commit `f7b30515157c6affd73e1d3cb3027ff54017096b`; GitHub Actions remains the authoritative source for CI status.

Native CPU/VM execution and Hub scheduling are now implemented; the next work is concrete host transports, deeper native architectural execution, and real trained-model validation.

## Qwen3 native runtime

Qwen3 remains the first model being taken through the full native-runtime path because it is currently assigned to the Coreless CPU role.

Implemented and green at the software/runtime boundary:

- native Qwen3 configuration/model compatibility
- native Qwen3 tokenizer boundary
- Q/K normalization
- RoPE with position offsets
- tied word embeddings
- storage-backed safetensors/model-weight loading
- native Qwen3 forward path
- greedy text generation
- native KV-cache generation
- cached causal masking
- grouped-query-attention KV-cache layout and regression coverage
- TensorRuntime RMSNorm
- TensorRuntime rotary trig, masking, scalar scaling, and argmax routing
- TensorRuntime scalar broadcast and transpose primitives used by Qwen3
- official Qwen3-0.6B artifact validation
- managed artifact acquisition
- immutable artifact revision pinning
- SHA-256 verification
- atomic `.part` downloads
- real-artifact integration runner
- metadata validation entry point

**Important:** green CI does not prove that the official trained Qwen3-0.6B weights have completed successful end-to-end inference. That remains a separate validation milestone.

### Qwen3 real-artifact validation issue to revisit

The official Qwen3-0.6B artifact was downloaded to the Lubuntu development VM and all required files were present. A manual SHA-256 check produced:

`f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b`

The extra trailing `b` means the downloaded `model.safetensors` did **not** match the pinned Coreless SHA-256:

`f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874`

The mismatched weights were removed during troubleshooting, and restoring the exact pinned artifact was not completed. The Hugging Face/native numerical reference comparison was therefore **deferred**.

**Do not spend development time on this now.** Revisit after the native Coreless execution boundary and remaining implementation work are complete. At that point, reacquire/validate the exact pinned Qwen3 artifact and perform the real forward/reference validation.

Do not commit large model weights.

## Model-as-hardware-component architecture

The intended lifecycle remains:

**large capable trained model → role-specific specialization → careful slimming → Coreless hardware-component integration → continuous user-specific static adaptation**

The model component must retain the capabilities necessary for its assigned hardware role. The VM is a containment/nesting environment, not the definition of the component.

Qwen3 is currently assigned to the CPU intelligence role. Future model components can specialize around GPU, storage, networking, communication, orchestration, or other machine roles.

## Remaining major work

### 1. Plug-and-play host transport integration

The reference software contract and transport adapter now exist. Continue with concrete cross-platform enumeration plus display/input/network transport adapters without moving computation into the host.

### 2. Native Coreless execution boundary

The public TensorRuntime boundary is now substantially deeper and is the immediate continuation point.

Completed in the current batch:

1. Coreless-native scalar broadcast and transpose primitives
2. Qwen3 RMSNorm routing through TensorRuntime
3. Qwen3 rotary trig, causal masking, scalar scaling, and greedy argmax routing through TensorRuntime
4. focused regression tests for these runtime boundaries

Verified status after code-and-test reconciliation (2026-10-22):

- Qwen3 KV-cache state is represented as per-layer Tensor objects, and when a TensorRuntime is bound, cache append uses `TensorRuntime.append_sequence`.
- Cache save/restore routes through `TensorRuntime.save/load`.
- Qwen3 head reshape/repeat and grouped-query attention route through TensorRuntime methods; grouped attention avoids explicitly repeating KV heads in the runtime path.
- Focused tests in `ai/test_qwen3.py` and `ai/test_tensor_runtime.py` cover cache append/equivalence, runtime-boundary calls, persistence/restore, GQA layout, and grouped-attention equivalence.

Therefore the earlier checklist to add these same API-level boundaries is complete and must not be restarted as if absent. Important limit: Tensor values still use Python numeric tuples, and several TensorRuntime operations are implemented with Python-level loops/fallbacks. This verifies the software/runtime boundary, not hardware-native data movement or trained-model end-to-end inference.

Remaining execution-boundary work should be tracked as a distinct future milestone: move supported operations onto genuinely native Coreless execution where available, profile and reduce host-side data movement, preserve deterministic fallback semantics, and add performance/correctness tests. Keep official trained Qwen3-0.6B inference as a separate, still-open validation milestone.

### 3. Real trained Qwen3-0.6B execution

After the native execution boundary is stable:

1. obtain/validate the official trained artifact through the managed artifact path
2. execute a minimal real one-token forward pass
3. verify output shape and numerical/runtime behavior
4. run short real generation using the native tokenizer and KV cache
5. optimize only after correctness is established

Do not mark live AI inference complete merely because CI is green.

### 4. Additional native model runtimes

Extend the native-runtime architecture to:

- DeepSeek
- gpt-oss
- Gemma
- Codestral

Each model should retain its native architecture internally while using the common AI-Core coordination interface.

### 5. Native Coreless operating environment

Continue:

- device drivers
- networking
- GUI
- remote display/input
- application environment

### 6. Scaling and compatibility

Continue:

- dynamic CPU/memory/AI/GPU scaling
- large persistent machine images
- multiple guest machines
- Coreless-native tooling
- x86-64 compatibility
- ARM64 compatibility
- binary translation
- guest OSes
- legacy virtualization

### 7. Final integration/conformance

Perform a final cross-layer audit covering:

- ISA/spec consistency
- vector/matrix encoding and execution semantics
- VM/capability semantics
- AI policy boundaries
- resource-control behavior
- telemetry/audit behavior
- terminal/session behavior
- model failure/cancellation behavior
- persistent machine state
- end-to-end Coreless execution

## Development rules

- Inspect the current repository before changing it.
- Batch related implementation changes.
- Do not trigger unnecessary CI runs while a known batch is still being constructed.
- When a test fails, determine whether the implementation or the test expectation is wrong before changing either.
- Keep architectural rules in specifications and implementation behavior in code.
- Never treat natural-language AI output as an authorization token.
- Never commit API keys or credentials.
- Keep local AI operation independent of the optional OpenAI backend.
- Do not substitute generic model implementations for native model architectures merely to make integration easier.
- Defer optional external-reference validation until the native implementation milestone is ready.

## Architectural goal

> **The Coreless computer is the computational architecture carried by persistent storage. The host provides the external interface; it is not the Coreless CPU.**

> **314DNest gives the computer a coordinated local intelligence layer without giving AI authority to bypass deterministic Coreless controls.**

## Resume point

Continue the **deep Qwen3/Coreless tensor execution boundary**, the **autonomous component/hub architecture**, and the **Lubuntu-first host platform adapter** work. VIGIL spatial-intelligence work is active again.

The Qwen3 KV-cache/head-data API boundary is implemented and covered by focused tests. Do not reopen the old “replace nested Python cache/head structures” task. Remaining open work is deeper native Coreless execution/performance validation and official trained Qwen3-0.6B end-to-end validation.

**Green resume point:** continue from the latest verified control-flow conformance checkpoint; do not infer CI status from documentation.**

Latest verified green checkpoint: GitHub Actions run #1244 on 2026-10-07; do not infer CI status from documentation-only changes.

Latest repository head:

`674ea90b251fdad141b338be880b644b21d89113`

This checkpoint includes the latest Qwen3/TensorRuntime transpose integration.

**Next session checkpoint:** prioritize Lubuntu/Linux native host integration and the existing Coreless milestones. VIGIL spatial-intelligence work (blueprint/floor continuity, sensor fusion, IR mapping, object-track association) is active again. Qwen3 cache/head API boundary reconciliation is complete; deeper native execution and official trained-model validation remain later checkpoints. Concrete host transport integration also remains open.

Do not restart from the older Qwen3-only handoff. The tensor runtime and Transformer routing work described above is already in `main`.

**Do not commit large model weights. Do not claim end-to-end trained-model inference until it has actually been executed and validated.**

## Documentation checkpoint — 2026-10-07: precise CALL/CALLR trap boundary

The Coreless-64 reference execution boundary now includes conformance coverage for misaligned CALL/CALLR targets. The step boundary validates the decoded target before executing the call, so a misaligned target raises the architectural alignment trap before link-register writeback. The existing direct `_execute()` contract remains unchanged for callers that exercise jump/call semantics directly.

The related conformance batch also covers precise misaligned jumps, reserved base encodings, arithmetic divide-by-zero/overflow behavior, EPC/TVEC trap transfer, and retirement suppression. The latest implementation fix is commit `f7b30515157c6affd73e1d3cb3027ff54017096b`, and its CI result should be verified from GitHub Actions rather than inferred from this document.

### Resume point

Continue from the latest green CI checkpoint after this trap-boundary batch. Preserve the precise-trap rule: architectural side effects must not become visible when an instruction traps before retirement. Next substantive work remains the deep Qwen3/Coreless tensor execution boundary, autonomous component/hub architecture, and concrete host transport integration.

## Plug-and-play host interface

The host interface is now a first-class architectural boundary. The host supplies only external services such as power/startup, display transport, keyboard/pointer/input transport, and network connectivity. Coreless remains responsible for CPU execution, memory, VM/OS execution, AI, persistent state, identity, policy, and component composition.

Target lifecycle: **connect → discover → verify Coreless identity → advertise capabilities → negotiate → attach → boot/resume → operate → detach**.

Normative design: `specification/host_interface.md`. Specification is complete; the software contract and cross-platform enumeration remain implementation work.


## Documentation checkpoint — 2026-10-06

The plug-and-play host boundary has advanced beyond the earlier identity/command milestone. The current reference transport layer now includes:

- transport-neutral Coreless identity frames
- capability negotiation and negotiated channel binding
- correlated device command/response frames
- raw encoded command exchange
- reusable `HostTransportSession` state
- session command exchange using the same wire command format
- session close that detaches external channels while preserving Coreless state
- automatic reattachment for command paths after disconnect

Relevant implementation files:

- `reference/device_protocol.py`
- `reference/device_command.py`
- `reference/host_interface.py`
- `reference/host_transport.py`
- `reference/test_device_command.py`
- `reference/test_host_transport.py`

The current host boundary is therefore a real transport-neutral software path, not only a written proposal. It still does **not** claim completed physical USB/PCIe/network enumeration or finished display/input/network hardware adapters.

Recent transport commits include `6259e4ec5393810e9879fb0122296259330ba347` (host transport sessions), `0dce9ae09ab74dc17b0d993af809efb37656889a` (session transport coverage), and `721cb941be0fe5b286610dec4a8cb51c583cfe8f` (correlated response helper coverage).

### Updated resume point

Continue the implementation rather than restarting the transport layer. The next transport work is concrete cross-platform enumeration and display/input/network adapters. In parallel, continue the native Qwen3/Coreless tensor execution boundary and VIGIL integration already described above.

Documentation-only status must not be used to infer a CI result; use the latest GitHub Actions run for build status.


## Documentation checkpoint — 2026-10-06: scheduler and dispatch throughput

The latest green checkpoint is GitHub Actions **#1124**, commit `5df0639e70e4c7ada1143146d5121ec2731e93f5`. The preceding scheduler snapshot implementation exposed one incorrect empty-scheduler test expectation; that test was corrected to register a real resource and verify the scheduler-owned `(capacity, load)` snapshot. The implementation was unchanged by that correction.

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

### Current resume point

Continue from the green throughput checkpoint. The next substantive work should improve the native Coreless execution path, tensor-backed Qwen3 KV-cache/head movement, concrete host transports, and persistent-storage-hosted execution. Preserve the scheduler throughput contracts above when extending compute distribution.


## Documentation checkpoint — 2026-10-07: Qwen3 tensor boundary completion

Repository inspection confirms that the native Qwen3 path already routes KV-cache append operations through `TensorRuntime.append_sequence`, uses TensorRuntime-native head reshape/repeat and grouped-attention movement, and provides persistent cache save/restore through the TensorRuntime storage boundary. The roadmap item is therefore marked complete rather than duplicating an already-implemented layer.

The next substantive work is concrete host transport adapters and persistent-storage-hosted execution, followed by the deferred official trained Qwen3-0.6B numerical validation. CI status must be read from GitHub Actions, not inferred from this note.


## Documentation checkpoint — 2026-10-07: persistent runtime environment

The persistent-storage-hosted reference runtime now has a direct launcher at `scripts/coreless-run.py`. It opens an existing Coreless machine image, resumes the persistent Coreless system, routes native shell commands, can advance the digital execution engine, and persists the resulting state. Regression coverage is in `reference/test_persistent_runtime.py`, including reopen/resume and shutdown persistence.

This closes the reference-runtime environment milestone without claiming that physical host-independent execution hardware exists. The image remains the authoritative persistent machine-state carrier; the reference execution engine remains the digital implementation boundary.

CI status must still be verified from GitHub Actions rather than inferred from this documentation.


## Documentation checkpoint — 2026-10-07: reference host I/O integration

The host boundary now has an end-to-end reference I/O path. `reference/host_io.py` provides deterministic display, input, and network transports plus Coreless input-event serialization. `CorelessHostInterface.bind_host_io()` binds those transports to negotiated capabilities, and `pump_host_io()` moves input, display, and network traffic across the boundary while Coreless remains the computational owner.

`HostTransportAdapter.connect()` and `open_session()` can bind the host I/O bundle alongside a persistent `CorelessSystem`. Regression coverage is in `reference/test_host_io_integration.py`.

Verified CI runs #1314 and #1315 are green. The next transport step is platform-specific host enumeration/adapters; the reference boundary should be preserved as the conformance target.


## Documentation checkpoint — 2026-10-07: platform-independent host discovery

Added `reference/host_discovery.py` and `reference/test_host_discovery.py`. The new `HostDeviceEnumerator` converts transport-neutral identity advertisements into validated, deterministic `HostEndpoint` objects. It derives Coreless device capabilities from the identity frame, preserves host capabilities/channels, rejects malformed advertisements and duplicate endpoint IDs, and remains independent of any physical bus.

This is the conformance layer between future platform-specific OS/device enumeration and the existing `HostTransportAdapter`. Physical adapters should produce discovery candidates and preserve the transport-neutral identity/command/session contracts already implemented.


## Documentation checkpoint — 2026-10-07: provider-backed host transport

`ProviderHostTransportAdapter` now bridges a platform discovery provider into the existing transport-neutral Coreless host boundary. Providers emit `HostDiscoveryCandidate` records; centralized discovery validation produces deterministic `HostEndpoint` objects before transport use. This keeps physical OS/device enumeration outside Coreless while giving future platform adapters a concrete integration point.

This milestone does not claim physical USB/PCIe/display/input/network adapters. The next host step is implementing concrete platform providers/adapters against this boundary while preserving the existing identity, capability, HostIO, command, and session contracts.


## Documentation checkpoint — 2026-10-07: atomic HostIO validation

The negotiated HostIO boundary now validates the complete negotiated display/input/network bundle before channel mutation and validates the input-router contract before binding. Regression coverage preserves the no-partial-attachment invariant. The latest reference-test checkpoint is green. Resume with concrete platform host providers/adapters while preserving the transport-neutral discovery, HostIO, command, and session contracts. Physical device support remains unclaimed.

## Resume checkpoint — 2026-10-23: spatial-intelligence work resumed

User explicitly resumed VIGIL spatial work. Do not treat the previous pause note as binding now; continue spatial engineering alongside other Coreless priorities.

Added `vigil/spatial_query.py` with `SpatialQueryEngine`, `SpatialQueryResult`, and `SpatialQueryStatus`, plus `vigil/test_spatial_query.py`. It returns nearest modeled feature/distance, associated level/zone, and optional nearby features after checking model/revision/frame, timestamp, freshness, pose state, and uncertainty. No-fix, stale, future timestamp, model mismatch, and degraded states are explicit. Exported the new API from `vigil/__init__.py`.

CI runs for implementation and tests must be checked before declaring this checkpoint green. Next spatial priorities: run the complete test suite; integrate query status into workspace/terminal or read-only web status; add explicit geometric region support; strengthen persistent blueprint/calibration records; then build actual sensor adapters and end-to-end synthetic replay. Real sensor hardware and field accuracy remain unvalidated.

Spatial follow-up added after query API: `vigil/spatial_regions.py` defines explicit versioned XY polygons with Z bounds; `query_region()` reports inside/outside only when model/revision/frame and pose freshness are valid. Unavailable or stale poses return `inside=None`. New exports are available from `vigil`. Region import/topology validation, workspace integration, persistent model/calibration storage, and real sensor adapters remain open.

## Spatial persistence follow-up

Added `vigil/spatial_registry_store.py` (`SpatialRegistryStore`) for SQLite persistence of normalized blueprint revisions, explicit regions, raster calibrations, and the active model pointer. `SpatialWorkspace(registry_store=store)` persists active-model imports/activation and region add/removal; a new workspace restores the saved active model/regions. Pose, live observations, and object tracks are deliberately transient and require fresh inputs after restart. Tests in `vigil/test_spatial_registry_store.py` and workspace restart tests cover the storage boundary. Latest workflow status must be checked for commit `8da9ef9` and subsequent integration/export/documentation commits.

## Active checkpoint — 2026-10-23: live spatial operator path

New implemented user-facing path:
- `vigil/spatial_snapshot.py`: versioned JSON snapshot with active model/floor geometry, pose state/freshness, object positions and trails, motion/presence state, uncertainty/source IDs, and explicit region membership.
- `reference/local_operator_server.py`: authenticated read-only `GET /api/vigil/spatial`. No session returns 401; POST is rejected; a missing workspace returns an explicit 503 instead of synthetic spatial data. CLI supports `--spatial-db` and optional `--blueprint`; the default SQLite spatial database sits next to the selected machine image.
- `operator-display.html`: live SVG map and object roster polled on the authenticated session. Current pose/objects, last-known stale markers, conflict indicators, feature markers, region polygons/membership, speed, last-seen age, uncertainty and source metadata are visible.
- Stale tracks are kept as last-known markers, not silently removed or treated as gone; stale motion is not reported as current. Stale markers remain out of current-evidence/readiness counts.

The code path and regression tests are in GitHub; check the latest runs for current HEAD before calling this newest snapshot fully green. Software fixture tests do not establish physical range, coverage, or tracking accuracy. Real HTTPS deployment plus actual sensors and calibrated blueprint are still needed to validate end-to-end operation. The complete product remains unfinished until those are proven.


## Current resume checkpoint — VIGIL spatial intelligence — 2026-10-23

**Spatial work is active.** The user's request explicitly unpaused it. Do not revert to the earlier paused status.

### Work now in the branch
- Confidence-aware model-frame location queries and explicit 3D-frame polygon regions are connected to the workspace and presentation.
- SQLite stores normalized blueprint revisions, regions, raster calibration metadata, the active model pointer, and bounded last-known object-track records.
- Authenticated `GET /api/vigil/spatial` supplies the browser map with model/floor features, pose state, object coordinates, speed, trails, stale/conflict state, uncertainty, region membership, and evidence metadata.
- Object evidence in the snapshot includes provenance, observation count, declared source-independence groups, calibration status/IDs, and whether lineage is declared. Operator object cards show it.
- Sensor-provider status is retained and exposed as `UNPOLLED`, `ONLINE`, or `ERROR`. Provider failure is shown rather than converted into invented readings.
- Persisted tracks are restored as `REACQUIRE`. Their coordinates remain last-known; fresh matching observations are needed before current-contact claims resume.
- Spatial endpoint freshness checks now use monotonic nanoseconds, matching the observation clock domain. The endpoint test fixture was updated too.

### Latest confirmed CI and current branch caution
- [Full reference suite passed — run 40005690022](https://github.com/buccees/Coreless-64/actions/runs/40005690022), commit `76cff07`.
- [Spatial documentation/spec test workflow passed — run 40005695887](https://github.com/buccees/Coreless-64/actions/runs/40005695887), commit `a7f9a5b`.
- [Run 40005685759](https://github.com/buccees/Coreless-64/actions/runs/40005685759) failed because it ran the clock implementation with an old wall-clock test fixture. The subsequent fixture update is green, so the identified test failure is addressed; still check the latest run after paperwork commits before claiming the newest HEAD is green.
- [Latest published Control Room workflow before this paperwork pass](https://github.com/buccees/Coreless-64/actions/runs/40005525144) succeeded. New documentation commits will trigger new runs.

### Immediate next steps
1. Check the newest Actions run after source-asset persistence and regression-test commits; report the actual result.
2. Measure and validate the sensor-mount transforms on actual hardware; the software now stores and applies explicitly selected rigid transforms, but their physical values must come from survey/calibration and be tested against real sensors.
3. Integrate the new checksummed `SpatialRegistryStore` portable bundle into the full Coreless OS/SSD snapshot, boot, and copy lifecycle; arbitrary image/CAD import adapters remain future work.
4. Implement supported live sensor adapters incrementally (camera/vision, UWB or other calibrated ranging, IMU, infrared, compatible Wi-Fi CSI). CSI is motion context, not a 3D location by itself.
5. Validate with a surveyed model and real sensors, then validate the authenticated HTTPS display against the active Coreless lifecycle.

### Newly completed since this checkpoint was first written
- `SpatialRegistryStore.export_portable_bundle()` / `import_portable_bundle()` now provide deterministic, checksummed registry migration for model revisions, regions, raster calibrations, sensor mounts, source asset bytes, object tracks/history, and active model. Tests cover complete round-trip equivalence, checksum corruption, and bundle-size limits. Full Coreless OS/SSD lifecycle integration is still required before this counts as a bootable machine snapshot.
- `SensorMountTransform` now validates a proper rigid 3D transform (orthonormal rotation with determinant +1 and metric translation), is stored immutably by model revision with checksum protection, and is applied through the explicit `ingest_sensor_local_object_observations(...)` path. Tests cover persistence/immutability, invalid rotations, translated/rotated point conversion, and rejection of mismatched sensor/frame/revision. These are software checks, not hardware calibration evidence.
- Saved raster calibration now connects to `SpatialWorkspace.ingest_calibrated_infrared_pixels(...)`. The method validates the active model frame/revision, maps timestamped pixel samples, records calibration and mount IDs as provenance, and passes the map into the existing workspace ingestion path. It deliberately does not claim to calculate/apply a physical sensor-mount transform.
- Deterministic synthetic replay tests now exercise pose updates, object tracking, region entry/exit, spatial-scene readiness, operator snapshots, evidence metadata, and repeatability. Run `40010789673` passed at commit `1840ca8`.
- `SpatialRegistryStore` now stores source assets as immutable, size-bounded byte records tied to a model revision, with media type, name, metadata, and SHA-256 checksums. Workspace blueprint import automatically preserves the exact original JSON manifest; tests cover checksum round-trip, immutability, size limits, and restart persistence. Newest source-asset CI runs are pending at the time of this checkpoint.

**Do not claim hardware proof.** Passing CI verifies software behavior, not actual object coverage, ranging accuracy, sensor calibration, universal detection, or physical unplug/replug. The desired view keeps stationary and moving targets represented; missing contact becomes stale/last-known, not silently “gone.”

## End-of-session handoff — 2026-10-24 evening / 2026-10-25 UTC

### Current branch and verified state
- Working branch: `vigil-spatial-awareness`. Do not merge to `main` unless the user explicitly asks.
- Current HEAD at handoff update: `5d82edd82c7e1af8c4a83059de16d9671f120531` — “Place Simulation Bay as section 04 in navigation.”
- Website: https://buccees.github.io/Coreless-64/
- Latest Pages deployment passed: [run 40148942978](https://github.com/buccees/Coreless-64/actions/runs/40148942978), for HEAD `5d82edd`.
- Latest automated test workflow passed: [run 40148943014](https://github.com/buccees/Coreless-64/actions/runs/40148943014), for the same HEAD.
- The navigation source now puts **04 // SIMULATION BAY** fourth and **05 // SENSOR INPUTS** after it. This fixes the source ordering/numbering. The user previously reported that the live phone page still showed Sensor Inputs fourth and no Simulation Bay; deployment success alone is not proof of what the browser serves. Independently confirm the live page on the next session before claiming the visible UI is fixed.
- The sensor request/response bridge is implemented in `index.html` and automated browser integration tests passed on earlier source commit `2d64c02` / test commit `3aa701a`. It supports focused radar/sonar/optical observation requests through `window.vigilSensorBridge.requestObservation(request)`, `window.vigilRequestSensorAction(request)`, or the `vigil:sensor-request` / `vigil:sensor-response` event pair. Responses withhold hidden ground truth.
- **Important boundary:** this proves the bridge and its tests, not that VIGIL autonomously decides when to request observations. Actual reasoning-loop integration is the next major task. The user wants a sensor simulation that works with VIGIL as a system demonstration/evaluation, not an isolated game.

### Next session — do these in order
1. Open the live website and independently verify the visible navigation on mobile and desktop. If the Simulation Bay tab still does not appear fourth, diagnose the deployed source/Pages configuration/cache rather than assuming a green workflow means the user sees it.
2. Inspect the actual VIGIL reasoning/agent path and identify the correct place to connect the existing sensor bridge. Avoid adding a second competing control path or inventing an autonomous loop without checking the current code.
3. Implement the smallest end-to-end loop: VIGIL reviews current contacts/evidence, identifies uncertainty, requests one follow-up observation using a suitable modality, receives the observation or miss, updates its assessment/track, and exposes a readable decision/event trail.
4. Keep simulation truth isolated to evaluator code; do not send hidden truth labels or internal vessel indices to VIGIL.
5. Run relevant browser tests and the full applicable test workflow. Inspect actual Actions results before pushing/claiming completion, per the user's explicit preference. Confirm deployment workflow success separately from live UI verification.

### Current simulation capabilities noted
- Sensor modes: radar, sonar, optical.
- Controlled clutter/false returns and evaluator-only truth mapping.
- Configurable detection probability (100%, 75%, 50%, 25%, 0%) and evaluation of misses/detection rate.
- Contact register and focused follow-up observations; observations can be published to Spatial Intelligence.
- Scene import/publish integration via `window.vigilImportScene(data)` is part of the existing work; validate it in the actual browser before claiming user-facing behavior.
- Existing implementation and earlier details are documented in the prior handoff sections above; inspect current code before changing anything.

### User workflow / communication
- The user prefers a collaborative partner approach and concrete execution, not unsupported assurances.
- **Check status/tests before every push.** State clearly what is committed, what CI passed, what deployment passed, and what has or has not been verified on the actual live page.
- Do not call the whole system “done” just because a workflow is green; hardware/live integration and autonomous reasoning are separate milestones.
