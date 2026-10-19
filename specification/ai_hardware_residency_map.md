# Coreless-64 AI-to-Hardware Residency Map

**Status:** architecture reconciliation draft — intended assignments recorded; model capability approval and runtime binding remain separate gates.

## Purpose

This document is the authoritative working map between AI model identities, their intended digital-hardware hosts, and the functions they provide. It separates design intent from implementation and evaluation evidence. A proposed assignment does not imply that a model artifact is installed, reachable, capability-approved, or already bound to the host.

## Operating rule: resident AI follows its host

A model assigned to a digital hardware component is integrated with that component's operational lifecycle. While the host is enabled and operational, the model binding and its assigned service remain active/available. Actual inference is scheduled when workload arrives; an idle host must not burn compute by generating tokens continuously.

A model with multiple assignments remains one logical model/runtime identity. Route requests to its assigned functions through the existing function router, scheduler, and compute fabric. Do not register duplicate copies of the same model just to represent multiple functions. Apply bounded concurrency only where overlapping work is actually required and supported by the backend.

The host's deterministic control logic remains authoritative for enable/disable, reset, dispatch gates, resource allocation, safety/policy checks, and status. AI output is not authorization to bypass those controls.

## Intended model/function map

| Model ID | Intended specialization / function | Assignment notes | Evidence status |
|---|---|---|---|
| `qwen3` | Primary CPU intelligence; main AI for Coreless CPU execution | Preserve its existing original assignment as well as the CPU role. The exact original non-CPU assignment must be reconciled from prior design records rather than replaced or guessed. | CPU role is documented; native instruction-execution binding and live trained-model validation remain incomplete. |
| `deepseek` (`deepseek-r1`) | Reasoning coprocessor and diagnostics | Specialized reasoning/diagnostic path; do not make it a universal default for every request. | Intended assignment; capability evaluation pending. |
| `gpt-oss` (`gpt-oss:20b`) | System services, structured requests, and tool-call handling | Route only the corresponding declared functions to this model. | Intended assignment; capability evaluation pending. |
| `gemma` (`gemma3`) | Input interpretation, with multimodal/image-input handling as a second assignment candidate | This is one of the models expected to serve more than one function. Confirm exact modality support against the deployed artifact before enabling the multimodal route. | Intended assignment; capability evaluation pending. |
| `codestral` (`codestral`) | Code/firmware generation, inspection, and repair | Keep coding work specialized; generated changes still require normal validation and authorization. | Intended assignment; capability evaluation pending. |

## Digital AI chipset integration

The digital AI chipset must have an AI model integrated with its component lifecycle; the deterministic chipset controller is not itself that model. Keep one canonical chipset/controller instance and use the existing registry, scheduler, and compute fabric rather than creating a second runtime.

The specific model identity assigned as the chipset's resident AI is **not yet established by the repository evidence inspected for this map**. Do not silently infer it from a model name or duplicate a model to fill the slot. Reconcile that identity against the user's original assignment records before changing runtime bindings. Once assigned, the model remains available while the chipset host is operational, and its requests pass through the same capability/policy gates and resource scheduling as other AI work.

## Assignment and lifecycle invariants

1. **Design intent is not capability approval.** Every route must be backed by evaluation of the exact deployed artifact and a declared capability.
2. **No name-based guessing.** Model IDs do not automatically confer CPU, chipset, GPU, communications, vision, or orchestration roles.
3. **Host lifecycle governs availability.** Host active means the resident binding is available; it does not require continuous inference while idle.
4. **One model identity, multiple declared functions.** Multiple assignments do not require duplicate registrations or model copies.
5. **Route by function.** Dispatch only to enabled models explicitly assigned to the requested function. Fail closed when no eligible assignment exists.
6. **Resource limits are selective.** Establish bounded concurrency only for models with real overlapping assignments/workloads. Do not fan every request out to all models.
7. **Hardware controls remain deterministic.** The chipset/controller and host CPU/VM/policy controls retain authority over dispatch, resource allocation, reset, and fault handling.
8. **Keep evidence honest.** Report intended, implemented, evaluated, and physically validated states separately. Reference tests do not prove trained-model quality or physical hardware operation.

## Next reconciliation gates

1. Recover the exact earlier Qwen3 assignment that must remain alongside CPU intelligence.
2. Recover the exact chipset-resident model identity from the original design records.
3. Identify the two multi-assignment models and their complete function lists; current working notes identify Qwen3 and Gemma as the expected pair, but Qwen3's second function still needs its original label.
4. Compare this intent map with `ai/function_router.py`, `ai/model_part.py`, and chipset dispatch. Implement only the missing bindings, preserving existing assignments.
5. Run per-artifact inference/capability evaluation before enabling each route, then test host lifecycle, fault behavior, and bounded concurrency for the models that need it.

## Related contracts

- `specification/ai_chipset_integration.md` — controller, motherboard status nets, scheduler/fabric dispatch.
- `specification/ai_function_routing.md` — explicit function declarations and fail-closed routing.
- `specification/model_capability_evaluation.md` — artifact identity and evaluation gates.
- `specification/component_architecture.md` — autonomous component and resident-AI lifecycle.
