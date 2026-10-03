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
