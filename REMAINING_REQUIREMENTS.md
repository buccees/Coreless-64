# Coreless-64 — Remaining Requirements Scope

**Scope baseline:** 2026-10-09  
**Repository:** `buccees/Coreless-64`  
**Working branch:** `next-host-network-adapter`

This document consolidates outstanding items from `ROADMAP.md`, `TESTING.md`, `TEST_ENVIRONMENT.md`, the host-interface and component specifications, and the project's recorded design goals. It separates the near-term completion gate from later platform, scaling, compatibility, and adaptive-model work so that future work is not confused with a requirement for the first end-to-end milestone.

A checked roadmap item or green reference CI run proves only the contract covered by that item or test. It does not by itself prove physical plug-and-play, a complete booted Coreless machine, or successful inference with a real trained model.

## Definition of completion

The first meaningful end-to-end completion milestone is reached when all of the following can be demonstrated together:

1. A persistent Coreless machine image can be opened, booted or resumed, execute its own machine/OS path, and preserve state across shutdown and restart.
2. Coreless owns architectural execution, memory, storage, VM/OS state, scheduling, capabilities, and authorization; the host supplies external I/O rather than acting as the computer.
3. A real trained local model can run through the Coreless/314DNest path on Coreless-managed resources, with numerical and generation behavior validated rather than inferred from unit tests.
4. Autonomous components can operate independently, compose through a Hub, dispatch work by capability, and detach/rejoin without losing local identity or state.
5. The reference host interface has a stable conformance contract, and the selected target platform has working discovery plus display, input, and network I/O adapters.
6. Persistence, capability/policy boundaries, recovery, and relevant failure paths have acceptance tests.
7. Specifications, roadmap, handoff, test instructions, and known limitations agree with the implementation.

The broader roadmap also includes VIGIL spatial input, adaptive model parts, multiple guests, scaling, and compatibility layers. Those are listed below as separate expansion tracks, not silently treated as prerequisites for the first end-to-end milestone.

## P0 — Resolve and close the end-to-end completion gate

### P0.1 — Canonical status and specification audit
- [ ] Reconcile contradictory/stale statements across `README.md`, `ROADMAP.md`, `HANDOFF.md`, `TESTING.md`, and `TEST_ENVIRONMENT.md`.
- [ ] For every requirement, record implementation location, verification evidence, and whether it is reference-only, platform-specific, or physically validated.
- [ ] Complete the final specification consistency audit and freeze normative Coreless-64 v1.0 contracts.
- [ ] Make the acceptance suite distinguish unit/reference success from end-to-end machine, physical adapter, and trained-model validation.

**Exit evidence:** a consistent requirements matrix and passing conformance suite; no documentation claim exceeds its evidence.

### P0.2 — Persistence integrity and failure atomicity
- [ ] Make multi-tensor Qwen3 KV-cache persistence safe against partial writes when a storage write fails; preserve the previous snapshot or reliably remove the incomplete new snapshot.
- [ ] Add fault-injection tests for failures at every write position, including cleanup/rollback failures, and define the resulting storage contract.
- [ ] Confirm tensor payload validation, legacy compatibility, cache restore continuity, and persistent machine-image recovery together.
- [ ] Validate large-image and reopen/resume behavior against documented limits.

**Exit evidence:** injected storage failures never leave an undetected mixed cache snapshot; successful persistence can be restored and validated after reopening the image.


### P0.2a — Coreless-managed storage regions and block-reuse policy

**Foundational invariant — stable storage home, upgradeable contents:** Coreless OS and CPU-related structures need stable, explicitly assigned storage homes, not permanently fixed payload sizes. Their contents and size may change during normal upgrades while their logical home identity remains stable. Growth must extend or reserve capacity under a defined region policy; unrelated rewriteable data must not overwrite or silently consume that home. A file-backed reference image can test logical ownership, but only a device adapter with suitable extent controls can claim stable physical placement. Ordinary SSD firmware may remap NAND internally, so physical-cell identity must not be claimed unless the target hardware actually exposes that guarantee.

- [ ] Define a Coreless storage-layout contract with explicitly assigned regions for immutable/model artifacts, configuration and boot metadata, durable machine state, checkpoint generations, high-churn KV caches/logs, and reserved/recovery capacity.
- [ ] Where the target storage device exposes controllable allocation units, assign stable block ranges or extents to those regions; record the mapping, ownership, permissions, capacity, and lifecycle in Coreless-managed metadata. Do not treat arbitrary allocator placement as the policy.
- [ ] Give each region an explicit write class: immutable/write-once, low-churn durable, transactional snapshot, or high-churn rewrite/append. Reuse blocks only under that region's declared lifecycle and reclamation rules; high-churn writes must not consume or rewrite protected durable-state blocks.
- [ ] Implement a Coreless allocator/reclaimer that tracks assigned, free, reserved, retired/bad, and in-flight blocks; enforce region boundaries and quotas and prevent one region from silently borrowing another region's protected capacity.
- [ ] Define device-adapter capabilities explicitly: block size, stable-address guarantees, flush/barrier semantics, atomic-write limits, discard/reset behavior, health/error reporting, and whether physical allocation units are actually controllable. Reject unsupported guarantees rather than pretending a file-backed reference image provides physical-block control.
- [ ] Make checkpoint publication transactional: write a new generation into its assigned region, validate it, flush it according to the device contract, then publish its manifest/pointer; retain the previous valid generation until the new one is committed.
- [ ] Add fault-injection tests for region isolation, quota exhaustion, interrupted writes, power-loss points, failed flush/publication, block retirement, recovery to the last committed generation, and cleanup of abandoned temporary data.
- [ ] Measure write amplification and reuse counts by region. Reuse high-churn blocks intentionally; protect immutable and durable regions from unrelated churn. Define wear/retirement policy for the actual target device instead of assuming a generic filesystem or SSD firmware satisfies Coreless's contract.

**Exit evidence:** a documented Coreless storage map and device contract; tests prove block ownership/reuse boundaries and recovery under injected faults. A file-backed simulator may validate allocation and transaction logic, but physical-block control is not claimed until a compatible target adapter and device demonstrate it.

### P0.3 — Real trained-model execution
- [ ] Validate an official trained Qwen3-0.6B artifact end to end: tokenizer/artifact loading, a real forward pass, and short generation.
- [ ] Compare output tensors/logits and generation against a trusted reference with documented tolerances and reproducible settings.
- [ ] Run the model through the intended Coreless/314DNest execution path on Coreless-managed resources, not only ordinary Python-side reference code.
- [ ] Measure memory use, execution limits, and failures; keep weights and credentials outside Git.
- [ ] Demonstrate the planned live multi-core/five-core inference path or document precisely what hardware/runtime prerequisite is still absent.

**Exit evidence:** reproducible artifact-backed numerical and generation results, plus a clear trace proving which operations and resources executed inside Coreless.

### P0.4 — Persistent machine end-to-end
- [ ] Demonstrate boot/resume, CPU execution, memory, persistent storage, OS/process lifecycle, and device services working together in the same machine image.
- [ ] Verify command execution, state mutation, shutdown, reopening, and state continuity through `scripts/coreless-run.py` and the documented runtime workflow.
- [ ] Define and test the minimal usable application/command environment for the first release.
- [ ] Distinguish services currently represented by reference models from services with real external device I/O.

**Exit evidence:** a documented clean-start → execute → persist → restart → verify scenario on a reproducible environment.

### P0.5 — Autonomous component and Hub integration
- [ ] Verify standalone operation and local state preservation across Hub disconnects.
- [ ] Verify Hub discovery, identity/capability aggregation, capability-routed work, pipeline dispatch, multi-vCPU scheduling, and fault isolation together.
- [ ] Verify failed component attachment, fault recovery, detach, and rejoin without corrupting the remaining composition.
- [ ] Define acceptance for composition changes while workloads are running and for unavailable capabilities.
- [ ] Validate cross-component execution beyond a single-process/reference-only simulation when suitable hardware/runtime is available.

**Exit evidence:** lifecycle and fault-injection acceptance tests demonstrate that components remain autonomous and the Hub never silently dispatches work to an ineligible component.

### P0.6 — Host I/O integration and target platform
- [ ] Select and document the first concrete host platform/OS target.
- [ ] Implement physical host/device enumeration providers for that target.
- [ ] Implement and validate platform display and keyboard/pointer/touch input adapters.
- [ ] Complete the platform network adapter and integrate it with the existing socket-backed/reference transport contract as appropriate.
- [ ] Exercise connect → discover → verify identity → negotiate → attach → boot/resume → operate → detach on the selected platform.
- [ ] Test hot unplug, unavailable channels, reconnect, malformed advertisements, and host-side I/O failures without moving CPU/OS/VM/AI authority into the host.

**Exit evidence:** a real target machine completes the lifecycle using actual platform I/O. The existing socket/reference transport tests alone do not satisfy this item.

## P1 — Operating environment and interaction

### P1.1 — Coreless OS/device services
- [ ] Implement the device drivers required by the selected target.
- [ ] Complete Coreless-owned networking beyond the current network-controller/reference transport foundations.
- [ ] Implement the initial GUI/display environment.
- [ ] Implement remote display and input.
- [ ] Complete the application environment and document the supported application ABI/runtime.

### P1.2 — VIGIL input and spatial services
- [ ] Implement gesture and multi-touch interpretation through VIGIL.
- [ ] Implement camera perception/tracking.
- [ ] Implement camera-based pointing.
- [ ] Implement spatial gesture recognition.
- [ ] Implement VIGIL spatial/world-model services inside Coreless.
- [ ] Preserve raw input access, optional VIGIL operation, capability checks, and deterministic regression coverage.

### P1.3 — Execution and tensor conformance
- [ ] Audit remaining Qwen3 elementwise and tensor operations against the intended TensorRuntime/Coreless execution boundary.
- [ ] Verify remaining head reshape/repeat, KV-cache, masking, and attention data movement through public architectural interfaces; avoid duplicate work where already implemented.
- [ ] Extend native vector/matrix tests through the public instruction/runtime boundary, including invalid shapes, overflow/precision contracts, and fallback behavior.
- [ ] Add deterministic replay validation that compares a replayed session against its original event/provenance chain.
- [ ] Validate traps, privilege/capability boundaries, and persistence contracts across integrated execution paths.

**Exit evidence:** an operation-by-operation coverage map links each required operation to its implementation, reference comparison, and regression test.

## P2 — Static-adaptive model parts and AI-derived hardware

### P2.1 — Model-part runtime
- [ ] Add architecture-specific native execution for Qwen3, DeepSeek/R1, gpt-oss, Gemma, and Codestral as supported by available artifacts and compute.
- [ ] Integrate model-part ABI, VM IPC, and capability enforcement.
- [ ] Implement the specialization planner.
- [ ] Persist user/workload adaptation state.
- [ ] Implement and validate slimming, pruning, and quantization paths.
- [ ] Establish the model-part regression/acceptance suite.
- [ ] Add adaptation history and rollback.
- [ ] Add explicit triggers for continuous workload adaptation.

### P2.2 — Bind model parts to actual Coreless resources
- [ ] Bind CPU-oriented model parts to Coreless-64 instruction execution.
- [ ] Bind GPU-oriented model parts to graphics/device/driver execution.
- [ ] Bind communication model parts to the user-session layer.
- [ ] Implement native architecture adapters.
- [ ] Validate live trained model components on the intended resources.

**Exit evidence:** each model part has an explicit ABI, capability envelope, execution target, reproducible acceptance tests, and rollback behavior. A model declaration or simulated endpoint alone is not completion.

## P3 — Scaling and multi-machine composition
- [ ] Implement dynamic CPU, memory, vector, AI, and GPU resource scaling.
- [ ] Validate large persistent machine images and define tested size limits.
- [ ] Support multiple guest machines.
- [ ] Support multi-device Coreless systems.
- [ ] Complete autonomous component hot-plug across Coreless Hubs, including state continuity, failure isolation, and scheduling updates.

## P4 — Compatibility and toolchain
- [ ] Implement a Coreless-native toolchain.
- [ ] Define and implement x86-64 compatibility.
- [ ] Define and implement ARM64 compatibility.
- [ ] Support selected guest operating systems.
- [ ] Implement binary translation.
- [ ] Implement legacy virtualization.

These are substantial compatibility programs. Each needs its own supported-version matrix, ABI/ISA contract, conformance suite, and explicit limits; they should not block the first Coreless-native end-to-end milestone unless the release scope explicitly requires them.

### P2.3 — AI-core selection and composition behavior
- [ ] Specify the AI-core component competition/selection contract, including deterministic tie handling and when a component may win repeatedly.
- [ ] Define how a selected core combines complementary strengths from contributing components and excludes unused or incompatible parts.
- [ ] Preserve provenance, validation, capability/policy checks, and rollback when composing or replacing parts.
- [ ] Add deterministic tests for selection, repeated tie wins, merge decisions, rejected contributions, and recovery after a failed merge.

**Exit evidence:** repeatable selection and composition decisions with a traceable provenance chain; no component gains authority to bypass Coreless policy.

### P5 — Deferred desktop experience
- [ ] Add an optional desktop theme based on the user's requested *The Gate* → *The Core* concept: a central gate/core motif, dark industrial atmosphere, restrained red/amber status lighting, and subtle motion.
- [ ] Make the theme communicate real AI-core/system states rather than decorative false status.
- [ ] Keep the theme optional and isolated from execution, persistence, and security contracts.

**Exit evidence:** a working, accessible theme integrated with the desktop/application environment after the underlying GUI exists. This is a deferred product/UI requirement, not a blocker for persistence or model validation.

## Full-project completion gate

The first end-to-end gate above is not the same as completion of the entire roadmap. The full project scope is complete only when the applicable requirements in **P0 through P5** have either passed their stated acceptance evidence or been explicitly removed from the agreed product scope. In particular, scaling, compatibility, adaptive model parts, VIGIL spatial services, platform I/O, and the desktop experience must not disappear from the plan merely because the first local-model demo works.

## Cross-cutting acceptance requirements

Apply these requirements to every track above:

- [ ] **Architectural authority:** AI output is a proposal, never authorization; deterministic Coreless policy and capabilities control resource access.
- [ ] **Persistence:** recovery after process restart, machine restart, partial failure, and malformed stored data is tested wherever applicable.
- [ ] **Determinism:** ordering, replay, tie-breaking, scheduling, and numerical tolerances are specified where correctness depends on them.
- [ ] **Fault handling:** failure tests cover cleanup, rollback, isolation, retry, and preservation of the original error.
- [ ] **Security:** malformed inputs, privilege boundaries, VM isolation, capability revocation, identity verification, and credential handling are tested.
- [ ] **Observability:** runtime state, dispatch decisions, model execution path, failures, and audit/provenance are inspectable.
- [ ] **Performance:** establish baseline measurements and regression thresholds for scheduler throughput, tensor operations, persistence, and end-to-end inference.
- [ ] **Reproducibility:** test environment, model artifact provenance, configuration, and commands needed to reproduce acceptance results are documented.
- [ ] **Documentation/handoff:** update the existing README, roadmap, testing instructions, specifications, and HANDOFF after meaningful green milestones. Do not create a separate `Paperwork.md`.

## Recommended execution order

1. Close P0.1 scope/status contradictions and keep the current CI gate authoritative.
2. Finish P0.2 transactional cache persistence with injected storage failures.
3. Complete the P0.3/P0.4 real-model and persistent-machine integration path, recording any hard blockers explicitly.
4. Run P0.5 Hub/component acceptance as an integrated lifecycle.
5. Choose one target platform and finish P0.6 physical host I/O rather than broadening socket-only edge-case tests without a contract failure.
6. Complete P1 OS, VIGIL, and execution-conformance work according to the target release.
7. Implement P2 adaptive model parts, then P3 scaling and P4 compatibility as separate milestones.

## Scope discipline

- Do not mark a requirement complete because a related helper, reference adapter, or unit test exists; use the exit evidence specified above.
- Do not claim physical hardware support from transport-neutral discovery or in-memory I/O.
- Do not claim live trained-model inference from CI or synthetic weights.
- Do not re-open completed socket lifecycle work without a concrete uncovered contract or regression.
- Keep model weights, secrets, and credentials out of the repository.
