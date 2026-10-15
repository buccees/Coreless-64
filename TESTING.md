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
- virtual Arduino protocol v1 lifecycle: command/read acknowledgements, sensor events, malformed frames, sequence replay rejection, disconnect safe-state behavior, reconnect sequence guard, and virtual input values

## Virtual Arduino lifecycle simulator

`reference/arduino_simulator.py` provides a deterministic software model of the newline-delimited Arduino bridge protocol. Simulator tests are in `reference/test_arduino_simulator.py`; bridge-to-simulator integration tests are in `reference/test_arduino_integration.py`. GitHub Actions [run #2007](https://github.com/buccees/Coreless-64/actions/runs/38790610629) passed with **695 tests**. The four integration tests cover command acknowledgements and sequence correlation, digital/analog reads, sensor events, disconnect safe-state reset, reconnect replay protection, and sequence preservation after a failed disconnected write.

The simulator validates protocol behavior only. It does not validate electrical behavior, physical serial timing, a real Arduino board, or platform-specific serial discovery. Those remain open.

## Not yet validated

- concrete cross-platform host enumeration and physical display/input/network transports
- physical Arduino board, electrical behavior, serial timing, and platform-specific serial-port discovery
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

## Physical Arduino bring-up checklist (pending hardware)

This checklist is prepared for the first real-board session; **none of these hardware checks have been run yet**.

1. Record the exact board model, MCU/logic voltage, firmware revision, host OS, serial-port name, and USB/serial adapter details.
2. Confirm the board's documented voltage limits and pin capabilities before wiring. Begin with external loads disconnected; use only a known-safe onboard LED or a correctly current-limited indicator circuit for the first output check. Do not drive motors, relays, or other high-current loads directly from GPIO.
3. Build and upload the reference sketch for the exact board. Confirm the configured serial rate (115200 baud) at both ends and verify the expected device identity/protocol version.
4. Start with one digital output and verify its acknowledgement and physical state. Then test a digital input and an analog input using a known-safe voltage within that board's specified input range.
5. Verify malformed commands are rejected without unintended pin changes. Record the response and resulting pin state for each case.
6. Disconnect the serial link and confirm the physical output behavior matches the documented firmware safe-state policy. Reconnect and verify that stale commands are not replayed and fresh commands work.
7. Repeat unplug/replug and reset tests; capture logs and record any differences between the real device and VirtualArduino.
8. Only after the basic checks pass, consider additional pins or external circuitry, with the relevant electrical protection and load drivers in place.

**Exit criteria:** attach test logs, board/firmware details, and observed electrical behavior before changing the hardware-validation status from pending. Software CI alone cannot satisfy this checklist.
