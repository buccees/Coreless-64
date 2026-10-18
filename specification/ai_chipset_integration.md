# Coreless-64 motherboard AI chipset attachment contract

**Status:** software compute integration exists; physical chipset attachment is pending identification and implementation.

## Correct insertion point

The intended physical AI chipset is a compute backend for the existing Coreless machine, not a second AI runtime and not a direct authority over the motherboard's safety controls.

```text
PersistentAIRuntime / AICoreRegistry
          |
          | model/session policy and request contract
          v
CorelessMachine -> AIComputeFabric -> MachineScheduler -> MachineWorkDistributor
                         ^
                         |
           physical AI backend adapter
                         |
              shortest supported local bus
                         |
                motherboard AI chipset
```

The software model already has `AIComputeResource` in `ai/compute_fabric.py` as the resource contract and `AIComputeSchedulerResource` in `scheduler.py` as the scheduler-facing adapter. Registered software AI cores currently enter through `CorelessMachine.attach_ai_registry()`. A physical backend should implement the existing compute-resource contract and be registered through the same fabric/scheduler path; do not create a parallel machine, registry, or scheduler.

## Dispatch contract

- Give the hardware backend a stable resource ID and explicitly declared operation/capability set. Never advertise tensor or inference operations the device/driver cannot execute.
- Keep Coreless as owner of scheduling, permissions, request validation, model identity, persistent sessions, result provenance, and fallback policy.
- Define fallback explicitly per operation. For operations that require the physical accelerator, fail clearly if it is unavailable; do not silently claim the hardware ran when a software core handled the work.
- Translate requests/results at one driver boundary. Use the chipset's shortest supported local interface; do not route on-board transactions through TCP, a remote AI service, or an unnecessary serialization broker.
- Keep device discovery, reset, timeout, error reporting, and removal/recovery in the backend adapter. Device loss must release scheduler capacity and must not corrupt the persistent AI session.
- The hardware driver may report health and readiness, but must not decide whether supply rails are electrically safe or release the machine's hardware reset.

## Power, reset, and readiness

The chipset power-enable/reset path is governed by the board's power supervisor and sequencing contract, independently of the AI runtime. The backend becomes dispatchable only after all of these are true:

1. Required rails are power-good and the chipset's documented power sequence has completed.
2. The chipset reset/boot protocol reports ready according to its datasheet.
3. The driver has identified the expected device and negotiated/validated its interface.
4. The backend has registered its actual supported operations and capacity with the Coreless scheduler.

On brownout, reset, timeout, or disconnect, stop dispatch to the device and report unavailable. Any orderly model/session checkpoint is best-effort software behavior, not a substitute for hardware power-fail protection.

## Facts required before implementing a real driver or schematic

- Manufacturer, exact part number, silicon revision, package, and datasheet.
- Supported local interface and electrical signaling: for example PCIe, USB, SPI, I2C, or a documented proprietary interface. Do not assume one.
- Pinout, voltage domains, I/O tolerance, rail current/inrush, sequencing, reset polarity/timing, clock requirements, and thermal limits.
- Boot firmware, runtime/driver API, command and result formats, memory/DMA rules, interrupt behavior, and error/recovery protocol.
- Supported operations, numerical constraints, concurrency/capacity, and whether the device runs an entire model or only selected kernels.
- Board switch/routing inventory and default/fail-safe state for power, reset, bus isolation, and device enable.

No pin mapping, part selection, voltage, or timing value should be guessed in advance of these facts.

## Acceptance tests

- Software contract test registers a backend, dispatches supported work, preserves work/model IDs and result provenance, and rejects unsupported operations.
- Scheduler test proves unavailable/reset devices receive no new work and are removed from eligible capacity; recovery requires revalidation before dispatch resumes.
- Explicit hardware-only preference fails rather than silently using a different backend when hardware is absent.
- Power/reset safety remains functional with the OS, desktop, registry, or AI process stopped.
- Bench acceptance measures rails, sequencing, reset, bus signal integrity, readiness, sustained workload, thermal behavior, disconnect, and brownout with the selected part.
- Software tests validate the adapter contract only; they do not count as physical chipset validation.
