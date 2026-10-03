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
- Transformer → TensorRuntime routing
- autonomous component identity, lifecycle, fault isolation, and hub workload dispatch

## Not yet validated

- complete plug-and-play host discovery/identity/negotiation/attach implementation
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

1. Add focused tests for the **native Coreless execution boundary** between TensorRuntime/Transformer operations and the public Coreless vector/matrix architectural interface.
2. Add `CorelessHostInterface` tests for identity handshake, capability negotiation, attach/detach, and external I/O channel binding.
3. Exercise autonomous components through hub composition and standalone detachment.
4. After those boundaries are stable, perform real Qwen3-0.6B forward/generation validation.

Do not mark live inference complete from CI alone.
