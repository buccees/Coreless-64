# Coreless Testing

## Current checkpoint

Reference/CI testing validates the software implementation. It does not by itself prove execution of a complete persistent-storage-hosted Coreless computer or live trained-model inference.

## Covered foundation

- Coreless-64 ISA and execution
- memory/MMU/privilege/interrupts/atomics
- vector and matrix execution
- multiprocessing and shared RAM
- persistent machine state and checkpoint/restore
- virtualization/VM capability boundaries
- firmware/boot/reference OS lifecycle
- 314DNest coordination/policy/capabilities/telemetry/audit
- persistent TensorRuntime
- native vector and supported matrix routing
- TensorRuntime RMSNorm, scalar broadcast, and transpose primitives
- Qwen3 rotary, masking, scalar scaling, and argmax runtime boundaries
- Transformer → TensorRuntime routing
- autonomous component identity, lifecycle, fault isolation, hub workload dispatch, native CPU/VM execution, and multi-vCPU Hub scheduling
- reference host enumeration, capability negotiation, channel binding, and transport readiness

## Not yet validated

- concrete cross-platform host enumeration and physical display/input/network transports
- tensor-backed Qwen3 KV cache and fully native head reshape/repeat/data movement
- official trained Qwen3-0.6B end-to-end inference
- complete persistent-storage-hosted Coreless runtime environment
- live five-core inference on Coreless

## Reference tests

```bash
python -m pytest
```

## Live local AI

Once the actual Coreless runtime environment exists and local model weights are installed outside Git:

```bash
python3 scripts/live-inference.py
```

Expected path:

**Coreless runtime → 314DNest → AI-Core Registry → local models → group result → deterministic policy**

AI output is never authorization.

## Immediate next test targets

1. Extend concrete host transport adapters while preserving the Coreless-owned execution boundary.
2. Continue exercising autonomous components through unified lifecycle, scheduling, detachment, and rejoin.
3. Extend the Qwen3 tensor boundary: KV cache, head reshape/repeat, and attention data movement.
4. Extend native vector/matrix execution coverage through the public architectural boundary.
5. Perform real Qwen3-0.6B forward/generation validation.

Do not mark live inference complete from CI alone.


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

## Throughput regression targets

- scheduler resource-state snapshots remain atomic and scheduler-owned;
- eligible-capacity calculations preserve capability and model affinity;
- worker sizing never exceeds executable resource capacity;
- single-item dispatch avoids unnecessary worker-pool setup;
- queue behavior preserves input/result ordering and fallback semantics.


## Persistent image sizing and reopen evidence — 2026-10-15

Reference tests exercise a **16 MiB sparse-RAM machine image** by writing data at the first and final RAM pages, saving machine state, reopening the image, and verifying RAM and CPU state resume. The test also verifies that reopening the same image with a different configured RAM size is rejected.

This establishes a tested 16 MiB sparse-image case, **not a maximum supported image size**, a performance guarantee, physical block-allocation control, or proof of a full end-to-end Coreless machine on hardware. The file-backed image serializes its object map as JSON/base64; larger-image performance and practical limits still need measurement.

- PR validation: GitHub Actions **#2043**, commit `fd021749558cb980f0d5fb8389816d06da7678e7` — success.
- Push validation for the same commit: GitHub Actions **#2042** — success.
- Added tests: `test_large_sparse_machine_image_reopens_and_resumes_state` and `test_reopen_rejects_ram_size_mismatch`.
- Physical hardware and official trained-model execution remain unvalidated.


## Logical storage-region policy — 2026-10-16

The reference storage layer now exposes `StorageRegionPolicy` for explicit logical namespace classification. A region is registered with non-overlapping directory prefixes and an immutable/writable policy. Unknown object names fail closed; writes to immutable regions are rejected.

Reference tests cover region classification, immutable-region rejection, writable-region acceptance, overlapping-prefix rejection, and unclassified-name rejection.

**Scope limit:** this is a logical policy primitive, not yet integrated into every storage write path. It does not reserve physical blocks, enforce per-region capacity, implement block reuse/reclamation, or guarantee transactionally isolated checkpoint generations. Those remain follow-on work; file-backed CI is not physical-storage validation.
