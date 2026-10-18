# Coreless-64 digital AI chipset integration contract

**Status:** the first software implementation is integrated into the existing machine runtime and virtual motherboard. This is a programmable digital controller, not a physical AI chip and not a second AI runtime.

## Canonical execution path

```text
PersistentAIRuntime / AICoreRegistry
          |
          v
CorelessMachine -> DigitalAIChipset control gate
          |                    |
          v                    v
MachineScheduler -> AIComputeFabric -> registered AI core
          |
          v
VirtualMotherboard logical status nets -> Coreless-side status inputs
```

The controller lives in `reference/digital_ai_chipset.py`. The machine owns one instance at `CorelessMachine.ai_chipset`; `CorelessSystem.ai_chipset` aliases that same instance. Status bits are driven through the canonical `VirtualMotherboard` netlist. The controller does not create a new model runtime, registry, fabric, scheduler, or motherboard.

## Control and status

- Stable identity: `coreless.digital-ai-chipset`; interface version 1.
- Controls: enable, disable, reset controller state, and clear fault.
- Status: ready, busy, fault, enabled, registered models, last work/resource IDs, and completed/failed work counts.
- Status outputs `ready`, `busy`, `fault`, and `enabled` are resolved through named logical motherboard nets and readable at Coreless-side input pins.
- Readiness requires the controller to be enabled, not faulted, and at least one AI resource to be registered.
- Reset clears controller fault/last-work state only. It does not erase AI sessions, model state, or machine persistence.

## Dispatch contract

- The controller accepts only the operations explicitly declared in `SUPPORTED_OPERATIONS`.
- Work must identify a registered model. The controller dispatches through the existing `MachineScheduler` with `ai_only` and fallback disabled; it does not call a model directly or silently substitute conventional CPU execution.
- The returned result must identify the requested work, operation, and model, and the scheduler allocation must identify the expected AI resource. Dispatch errors increment the failed count and latch a fault until cleared/reset.
- Coreless retains policy, authorization, model identity, persistent sessions, scheduling, and result provenance. AI output is not authorization.
- Local components communicate by direct in-process calls. No TCP, network broker, physical bus, chip pinout, or electrical model is implied.

## Verification

`reference/test_digital_ai_chipset.py` covers canonical motherboard wiring/status, dispatch through the existing fabric and scheduler, provenance, unsupported operations, and controller enable/reset/fault controls. `reference/test_virtual_motherboard.py` verifies the new logical signal continuity alongside existing reset/clock/IRQ/GPIO paths.

These tests validate software control logic and digital netlist behavior only. They do not validate physical power detection, USB enumeration, real electrical behavior, or trained-model quality.