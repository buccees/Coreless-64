# Coreless

## Live project website

**Open the live project website:**

[🌐 LAUNCH CORELESS-64 / VIGIL WEBSITE →](https://buccees.github.io/Coreless-64/)

> GitHub does not allow an interactive website iframe inside a README. Use the prominent link above to open the live site; the iframe markup below is retained as a fallback for Markdown viewers that support it.

<iframe src="https://buccees.github.io/Coreless-64/" title="Coreless-64 and VIGIL project website" width="100%" height="720" loading="lazy" style="border:1px solid #30363d; border-radius:8px;"></iframe>

If the embedded view is not displayed by your Markdown renderer, use the [live website link](https://buccees.github.io/Coreless-64/) directly. GitHub's README renderer may sanitize iframe elements; the website itself is published separately through the repository's GitHub Pages workflow.

## Current verified checkpoint — 2026-10-24

The latest carrier workflow has passed its QEMU/UEFI boot and simulated power-cycle recovery checks. The recovery fixture verified all three exact values after the second boot:

- **Virtual CPU register:** `r7 = 37`
- **Virtual program counter:** `260` (`0x104`)
- **Virtual RAM marker:** eight bytes, `CORELESS` (`434f52454c455353` in hexadecimal)

The automated workflow also confirmed that the booted carrier reached multi-user mode, launched the Coreless console, and restored the existing persistent machine state. The reference test workflow passed on the same checkpoint.

- [Latest successful UEFI carrier and recovery workflow](https://github.com/buccees/Coreless-64/actions/runs/40100765232)
- [Latest successful reference test workflow](https://github.com/buccees/Coreless-64/actions/runs/40100765455)
- [Carrier build and test specification](specification/bootable_carrier.md)
- [Project roadmap](ROADMAP.md)

**What this proves:** the current Linux-based UEFI carrier can launch the Coreless reference runtime, open its persistent machine image, and recover the tested virtual CPU and RAM state across a simulated power cycle.

**What it does not yet prove:** native Coreless-only boot, physical removable-SSD boot, full program continuation after interruption, trained Qwen3-0.6B end-to-end inference, or comparative performance benchmarks. The current recovery values are functional correctness checks, not throughput or latency benchmarks. Those remain engineering and validation work.

The architectural direction remains a **software-defined machine**, not simply an application: Coreless is developing its own virtual processor and execution model, memory, devices, OS/runtime, AI integration, and persistent state. The host provides physical resources for the current reference implementation while work continues toward Coreless-controlled execution.

---


[**Coreless-64 album cover artwork — Claude**](./Coreless-64%20album%20cover%20artwork%20-%20Claude.html)

**The SSD is the Coreless-64 machine. It carries the complete machine—not merely files or saved state—including its execution engine, operating environment, configuration, and persistent state. The operating system runs on that machine. Lubuntu is the preferred OS, not the host that owns or runs Coreless as an application.**

> **The SSD holds the whole Coreless-64 machine. The execution engine and OS are part of that machine. External hardware provides the physical interfaces needed to power, connect, and operate it; it does not redefine the machine as a program running on the host.**

## Coreless-64

**Permanent interface rule:** the SSD carries the complete machine, including its execution engine and OS. The machine should need only a monitor/display and I/O connections to be used. External equipment provides display and I/O—not the computer's execution engine or architectural authority.

Coreless-64 is the 64-bit Coreless architecture. The repository contains its digital reference execution engine, persistent machine model, operating-environment foundation, virtualization, devices, vector/matrix execution, and 314DNest local-intelligence layer.

The SSD is the authoritative carrier of the complete machine. Do not reduce it to a boot disk, passive data drive, or state-only container.

## Autonomous component architecture

Coreless is also designed as a **composable computer made of autonomous Coreless components**.

Each component is intended to be a complete Coreless unit rather than a passive peripheral. A component can carry its own execution, memory/storage, VM boundary, AI runtime/model, role specialization, and communication identity.

Components therefore support two modes:

- **Standalone:** a component can operate independently.
- **Unified:** multiple components can connect through a Coreless Hub and form a larger Coreless computer.

A component retains its identity and specialization when connected. Disconnecting it must leave it capable of independent operation, and reconnecting it must allow discovery and composition again.

Per-component AI is part of this architecture. Models can specialize around the role of their component, with training/adaptation occurring inside the component VM where appropriate. Coreless architectural, VM, capability, and policy controls remain authoritative.

The initial software boundary is implemented in `reference/components.py` and specified in `specification/component_architecture.md`.

## Current status

The repository is at the current implementation checkpoint; CI status is tracked by GitHub Actions rather than frozen in this document.

Latest confirmed integration commit:
`e3ee0676e6045963e1004940326730ed4af7a067`

The current implementation includes:
- Coreless-64 ISA and variable-length instruction framing
- CPU, memory, privilege, interrupts, atomics, vector and matrix execution
- multiprocessing, persistent storage, virtual RAM, devices, graphics/network foundations
- VM isolation, IPC, shared-memory capability control and hypervisor lifecycle
- firmware, boot, reference OS/process/memory lifecycle
- checkpoint/restore and machine resume
- coordinated Hub checkpoint commit verification with failed-publication manifest rollback
- 314DNest coordination, policy, capabilities, telemetry, audit and sessions
- persistent Coreless TensorRuntime
- native vector add/multiply and deterministic vector dot
- supported-shape native integer matrix execution
- TensorRuntime scalar broadcast and transpose primitives
- Coreless-native RMSNorm, reciprocal/rsqrt, rotary trig, masking, scalar scaling, and deterministic argmax boundaries
- Transformer execution routed through TensorRuntime
- Qwen3 runtime with GQA, KV cache, rotary attention, RMSNorm, SwiGLU, generation, and progressively deeper TensorRuntime execution
- autonomous Coreless component identity, specialization, hub discovery, connect/disconnect, composition metadata, fault isolation, capability-routed workload dispatch, and native CPU/VM execution

**Important:** green CI is not proof of live trained-model inference. Official trained Qwen3-0.6B end-to-end execution remains unvalidated.

## Plug-and-play computer interface

Coreless now treats the host connection as a narrow external interface: power/startup, display transport, keyboard/input transport, and network/I/O transport. The host does not supply Coreless CPU, RAM, OS execution, VM execution, AI computation, or architectural authority.

The target plug-and-play lifecycle is: **connect → discover → verify Coreless identity → advertise capabilities → negotiate interfaces → attach → boot/resume → operate → detach**.

The normative target is documented in `specification/host_interface.md`. Lubuntu is the preferred OS to run on the machine during initial bring-up, not the definition of the machine or a host OS that owns its execution. The portability target is a Coreless machine that can boot its own OS from a broad range of supported SSDs and expose its own device identity through appropriate hardware interfaces. Storage/enclosure identity is distinct from persistent Coreless machine identity and from any optional physical device-mode identity. An ordinary SSD cannot present itself as a separate USB computer without compatible device-side hardware/firmware. The reference host transport adapter and channel-binding contract are implemented; physical platform enumeration and concrete display/input/network transports remain open.

## Bootable SSD carrier milestone — 2026-10-23

The first x86-64 UEFI carrier-image builder is now implemented in `scripts/build-bootable-ssd.sh`. It creates a GPT disk image with an EFI System Partition and Linux root filesystem, installs the boot chain, copies the Coreless-64 repository onto the image, and enables the Coreless machine console service. The console starts the Coreless reference execution engine and stores its persistent machine image on the carrier.

- Build specification: [specification/bootable_carrier.md](specification/bootable_carrier.md)
- Build script: [scripts/build-bootable-ssd.sh](scripts/build-bootable-ssd.sh)
- Image workflow: [Coreless bootable carrier workflow](https://github.com/buccees/Coreless-64/actions/workflows/bootable-carrier.yml)
- Latest image-build run: [40012528792 — passed](https://github.com/buccees/Coreless-64/actions/runs/40012528792)

This is a meaningful first bootable-carrier milestone, **not yet proof of a fully native, bare-metal Coreless boot chain or a physical-SSD boot test**. The first prototype uses a Debian/Linux kernel as the hardware bootstrap and driver substrate, then launches the Coreless reference engine. Actual boot on a physical SSD, broader controller/firmware compatibility, and replacement of the Linux bootstrap with a native Coreless boot path remain open. Writing the image to a physical drive erases that drive.

## Next engineering checkpoint

The following priorities reflect the current implementation rather than the original milestone order:

1. **Portable host/storage compatibility:** implement and validate the first Lubuntu/Linux host adapter without making Linux a design limit; define a tested SSD/host compatibility matrix and keep storage identity distinct from Coreless machine identity. The transport-neutral contract exists; physical platform providers remain open.
2. **Hardware-level device identity:** specify and evaluate the physical interface needed for Coreless to enumerate as a distinct device to another host. Do not assume a standard SSD enclosure supports USB device mode; this requires compatible hardware/firmware and end-to-end validation.
3. **Remote Operator Display:** validate and extend the authenticated, read-only browser display against the active Coreless lifecycle and explicitly observed event sources. Never infer physical sensor connectivity from an available endpoint.
4. **Native execution and trained-model validation:** deepen native Coreless execution/performance validation, then run the official trained Qwen3-0.6B artifact end-to-end and validate live inference on Coreless resources.
5. **Model-part execution binding:** connect validated CPU/GPU/communication model roles to actual Coreless instruction, graphics/device, and user-session execution.
6. **Conformance:** complete the final ISA, persistence, capability, AI-control, host-interface, and end-to-end audit.

VIGIL spatial intelligence is active development. The current implementation includes blueprint/revision-aware queries and regions, persistent registry and last-known object tracks, calibrated IR mapping primitives, multimodal provider contracts, evidence-aware object tracking, and an authenticated operator snapshot. Deterministic end-to-end sensor replay, image/mount calibration integration, concrete sensor drivers, and real field accuracy remain open; passing CI does not establish physical sensing coverage or accuracy.

## 314DNest

314DNest is the local System Fabric coordinating AI cores with Coreless resources. AI output is never authorization:

**AI result → structured proposal → deterministic policy → capability check → Coreless resource → telemetry/audit**

Qwen3, DeepSeek, gpt-oss, Gemma and Codestral remain local model participants; GPT-5.6 Luna is optional through the OpenAI development adapter.

## Documentation

See `ROADMAP.md`, `TESTING.md`, `TEST_ENVIRONMENT.md`, `HANDOFF.md`, and the `specification/` directory for the current project record.

Do not commit model weights, API keys or credentials.


## Plug-and-play transport update — 2026-10-06

The reference host boundary now has a reusable transport-session layer in addition to identity and command framing. Coreless can enumerate a reference endpoint, verify its Coreless-64 identity, negotiate capabilities, bind channels, establish a `HostTransportSession`, exchange correlated command frames, and close the session without destroying Coreless machine state.

This is transport-neutral software infrastructure. It is intended to make the eventual USB, PCIe, network, storage-attached, and other adapters interoperable without moving CPU, RAM, OS, VM, AI, or architectural authority into the host.

The physical plug-and-play milestone remains open: cross-platform physical enumeration and concrete display/input/network transports are still to be implemented.


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


## Persistent runtime launcher — 2026-10-07

The repository now includes `scripts/coreless-run.py`, a direct launcher for a persistent Coreless machine image. It resumes the stored machine/OS state, accepts native Coreless shell commands, can advance the digital execution engine, and persists state or shutdown. The image remains the authoritative machine-state carrier and the host remains outside Coreless computational authority.


## Arduino physical I/O bridge — 2026-10-10

Coreless now has an initial Arduino serial bridge in `reference/arduino_io.py`. It defines a bounded, versioned newline-delimited JSON protocol for pin commands and device events, with device identity checks, monotonically increasing receive sequences, allowlisted GPIO operations, strict value ranges, and malformed-frame rejection. The adapter accepts a serial-port object, so applications may use pyserial without making it a mandatory dependency of the reference runtime.

Initial command set: `pin_mode`, `digital_write`, `analog_write`, `digital_read`, and `analog_read`. The matching reference firmware sketch is in `firmware/arduino/coreless_arduino_bridge.ino` and uses ArduinoJson 6.x. It demonstrates pin commands plus a periodic A0 sensor event. Physical-board validation and platform-specific serial-port discovery remain open.


The reference Arduino sketch uses a 115200-baud serial connection and a small line buffer suitable for low-RAM boards. Change its `DEVICE_ID` to match the host adapter's configured ID. Install ArduinoJson 6.x through the Arduino Library Manager before compiling.


The host-side `ArduinoInputAdapter` in `reference/arduino_io.py` now translates Arduino event frames into the existing Coreless `InputEvent` ABI and forwards them through the negotiated host input transport. Sensor/GPIO events default to `DEVICE_STATE`; firmware can emit supported typed input events with validated coordinates and fields. Acknowledgements are consumed without creating fake input events. Regression tests cover sensor forwarding, pointer events, acknowledgements, and malformed numeric data.
