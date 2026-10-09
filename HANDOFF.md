# Coreless-64 — Project Handoff

## Latest verified checkpoint — 2026-10-09: socket packet validation

GitHub Actions **#1770** passed on commit `c85b1cca92fff75e21aacb75f74069f8a10e3a60` (workflow: [Coreless reference tests](https://github.com/buccees/Coreless-64/actions/runs/37922079849)).

The socket-backed host network adapter now treats invalid outbound packet arguments as caller-side validation failures rather than transport failures:
- Only `bytes`, `bytearray`, and `memoryview` packets are accepted; arbitrary coercion such as `bytes(4)` is rejected.
- Oversized outbound packets are rejected before writing to the stream.
- These local validation failures leave a healthy socket transport usable for a subsequent valid packet.
- Actual socket send/receive failures and invalid incoming frame lengths still retire the transport.

The added regressions are in `reference/test_host_socket.py`. This is reference transport hardening only; it does not claim a physical platform network adapter is complete.

## Current state

The canonical consolidated scope is [`REMAINING_REQUIREMENTS.md`](REMAINING_REQUIREMENTS.md). Use it to sequence remaining work and define exit evidence; do not treat reference CI alone as proof of physical adapters or live trained-model inference.

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

Next priority:

1. move Qwen3 KV-cache storage from nested Python lists into TensorRuntime-backed state
2. add native head reshape/repeat and GQA cache movement primitives
3. move attention data movement away from direct host-side tensor data manipulation
4. preserve deterministic fallbacks where the runtime cannot yet execute a shape natively
5. add focused boundary tests before CI

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

Continue the **deep Qwen3/Coreless tensor execution boundary** and the **autonomous component/hub architecture** in parallel.

The immediate Qwen3 resume point is the KV-cache/head-data path: replace remaining nested Python cache/head structures with TensorRuntime-backed operations while keeping model semantics unchanged.

**Green resume point:** continue from the latest verified control-flow conformance checkpoint; do not infer CI status from documentation.**

Latest verified green checkpoint: GitHub Actions run #1244 on 2026-10-07; do not infer CI status from documentation-only changes.

Latest repository head:

`674ea90b251fdad141b338be880b644b21d89113`

This checkpoint includes the latest Qwen3/TensorRuntime transpose integration.

**Next session:** continue Qwen3 KV-cache/head data movement through TensorRuntime, then concrete host transport integration and real trained Qwen3-0.6B validation.

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


## Documentation checkpoint — 2026-10-08: socket-backed host network transport

The host transport boundary now includes a concrete socket-backed network transport in `reference/host_socket.py` and a socket-aware adapter in `reference/host_transport.py`.

Implemented and covered by the reference suite:

- deterministic 32-bit big-endian length framing;
- bounded packet sizes and retirement of transports receiving oversized frames;
- exact/partial socket reads and peer-close handling;
- send/receive failure and close-state handling;
- socket discovery and required network-channel validation;
- reconnect preservation and stale socket cleanup;
- guaranteed interface detachment when disconnect cleanup encounters a close failure;
- reusable session validation with explicit `require_channels(...)` checks for operations that require particular negotiated channels.

The latest validation-order failure was fixed in commit `2fa4433d26873e8f3b45e9c48e01a81b4f169967`: missing negotiated channels are now checked for membership before channel state is inspected, so the intended missing-channel contract error is raised instead of a `KeyError`.

**Verified CI:** GitHub Actions run **#1480** is green with **664 tests passed**.

### Current transport resume point

Continue only with socket lifecycle hardening that has a concrete contract or regression need. The first candidate is ensuring a newly constructed socket transport is cleaned up if the superclass connect path fails after construction. Memory ownership has already been handled and should not be revisited.

This milestone is limited to the host-side network transport boundary. It does **not** claim physical display/input implementation or physical USB/PCIe/bus enumeration.

### Current repository checkpoint

- Branch: `next-host-network-adapter`
- PR: #17
- Latest verified green commit: `2fa4433d26873e8f3b45e9c48e01a81b4f169967`
- CI: run #1480, 664 passed

Documentation status must not be used to infer CI status; verify GitHub Actions when resuming work.


## Documentation checkpoint — 2026-10-08: reconnect transaction hardening

Socket-backed host transport reconnect handling now validates replacement HostIO bundles before mutating an existing attachment. A failed reconnect caused by an invalid display/input/network transport or input-router contract therefore preserves the currently live session instead of clearing its channels first. Regression coverage was added in reference/test_host_transport.py.

The closed-raw-socket lifecycle check was also hardened: stdlib sockets are rejected when their fileno() reports a closed descriptor, while socket-like transports retaining an explicit closed property remain supported.

**Verified CI:** GitHub Actions runs #1514, #1515, #1516, #1517, #1518, and #1519 are green across the transport-hardening commits; the latest commit is 3987e1e092390fef900545dace4cfe44b3f3130b.

### Current transport resume point

The reconnect/HostIO atomicity checkpoint is complete. Continue with the next concrete socket lifecycle or transport-boundary contract; do not revisit memory ownership or the already-closed raw-socket regression unless a new failure requires it.


## Documentation checkpoint — 2026-10-08: transactional transport/session hardening

The reference host transport now preserves an already-live attachment across failed reconnect mutations at multiple boundaries. Replacement HostIO validation occurs before attachment mutation; host identity attachment restores its prior negotiated/host/system state on failure; transport channel rebinding restores the complete live attachment snapshot if a replacement bind fails; and HostIO channel binding restores its channel/router/HostIO/display state after a partial bind failure.

Socket-backed reconnect handling also closes replacement network transports when binding fails and preserves the prior live socket session until the replacement is known to be valid. Closed raw sockets are rejected consistently at adapter and reusable-session validation boundaries using both explicit closed-state properties and the standard socket `fileno() < 0` contract.

Regression coverage now exercises failed reconnect HostIO validation, channel rebinding rollback, partial HostIO channel-binding rollback, socket network rebinding rollback, and closed raw socket session validation.

**Verified CI:** GitHub Actions runs **#1552** and **#1556** are green for the latest transport-hardening fixes.

### Current transport resume point

The reconnect and session closed-channel atomicity work is complete. Continue with the next concrete socket/transport lifecycle contract or platform-provider integration. Do not revisit memory ownership or the closed-raw-socket regression unless a new failure requires it.

The host boundary remains transport-neutral above the concrete socket adapter and does not claim completed physical display/input/network hardware enumeration.


## Documentation checkpoint — 2026-10-08: session validation contract correction

The reusable transport-session validation boundary was rechecked after a regression exposed an overly strong invariant. Session `validate()` remains responsible for attachment identity, negotiated-state consistency, and detection of channels that are present but closed; it does not require every negotiated capability to currently have a bound channel. Explicit channel completeness remains the responsibility of `require_channels()`.

The regression coverage for a missing negotiated channel therefore exercises `require_channels()`, preserving the established session contract while still rejecting incomplete channel requirements deterministically.

**Verified CI:** GitHub Actions run **#1569** is green for commit `2cf39f92e6a9b9923a734f02d91902ea783884f0`.

### Current transport resume point

The corrective session-validation change is green. Continue with the next concrete socket/transport lifecycle or platform-provider contract. Preserve the distinction between session liveness validation and explicit channel requirements.


## Documentation checkpoint — 2026-10-08: socket transport hardening complete

The socket-backed host transport lifecycle hardening pass is complete at the reference boundary. Replacement socket construction failures now leave an existing live session intact; a later valid reconnect can recover normally. Send/receive transport failures retire the affected socket wrapper, cleanup errors do not mask the original transport failure, scoped cleanup preserves body exceptions, and disconnect detaches the Coreless interface even when socket cleanup reports an error.

Regression coverage exercises failed reconnect recovery, socket ownership across reconnects, closed-channel/session validation, transport retirement, and disconnect cleanup. **GitHub Actions run #1662 is green** for the final reconnect-recovery regression.

### Transport resume point

The reference socket lifecycle hardening is complete. Do not continue adding socket edge cases without a concrete contract failure. The next host-interface work is concrete cross-platform enumeration and platform display/input/network adapters.


## Documentation checkpoint — 2026-10-09: final socket transport hardening audit

The final reference-boundary audit is complete at commit `259569c8b20a3b9ad4a0252804c96dafe1bcad2a`. GitHub Actions runs [#1839](https://github.com/buccees/Coreless-64/actions/runs/37961186663) and [#1840](https://github.com/buccees/Coreless-64/actions/runs/37961193448) both passed.

The audit reviewed the socket framing implementation and adapter lifecycle against the current contract and the existing regression suite, including:

- 32-bit big-endian frame boundaries, empty packets, configured size limits, partial reads, and peer EOF;
- serialized concurrent sends and receives, plus close/error retirement during blocked I/O;
- bytes-like input normalization and invalid receive chunks;
- cleanup idempotency and preservation of the original transport/protocol exception when shutdown or close fails;
- shared-socket wrapper retirement, reconnect rollback/recovery, and interface detachment after cleanup errors.

No additional production-code change was justified by this audit. The recent targeted regressions for partial payload EOF, shared-socket wrapper retirement/usability, and oversized-frame errors surviving cleanup failures are green. The reference socket transport hardening task is therefore closed; do not add further isolated socket tests without a demonstrated contract gap or regression.

**Important boundary:** this closes only the reference socket transport/lifecycle hardening work. P0.6 remains open for selecting a real target platform, implementing physical host/device enumeration and platform display/input/network adapters, and validating the complete lifecycle on actual platform I/O. Reference CI is not evidence that physical plug-and-play hardware support is complete.

Resume with the concrete target-platform integration in `REMAINING_REQUIREMENTS.md`, not another socket-only edge-case batch.
