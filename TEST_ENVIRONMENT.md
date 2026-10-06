# Coreless Test Environment

## Current state

The repository has a reproducible **digital/reference** test environment. The separate milestone of executing the complete persistent-storage-hosted Coreless machine has not yet been validated.

## Reference setup

```bash
bash scripts/bootstrap-test-environment.sh
source .coreless-venv/bin/activate
python -m pytest
```

## Local AI setup

Use the repository local-AI setup tooling as documented by the current scripts. Model weights stay outside Git.

The live inference runner is:

```bash
python3 scripts/live-inference.py
```

## Actual Coreless runtime milestone

Still required:

1. persistent storage carrying the Coreless machine;
2. reproducible startup of the Coreless digital execution engine;
3. Coreless virtual CPUs, memory, storage and devices operating together;
4. display/input/network interfaces;
5. plug-and-play host discovery, identity, and capability negotiation;
6. local AI runtime and model weights outside Git.

This is distinct from ordinary Python/CI execution.

## Next

The immediate engineering targets are the **native Coreless execution boundary** and the **plug-and-play host interface**. Then validate a real official trained Qwen3-0.6B artifact and establish live runtime inference.


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

The reference environment currently validates the scheduler/distributor throughput layer through the same green reference-test workflow. This remains a digital/reference validation; it does not claim completion of the physical host interface or live trained-model inference.
