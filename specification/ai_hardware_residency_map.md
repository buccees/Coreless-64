# Coreless-64 AI-to-Hardware Residency Map

**Status:** architecture reconciliation draft. Confirmed design decisions, unresolved assignments, implementation status, and capability-evaluation evidence are kept separate.

## Purpose

This document tracks the relationship between AI model identities, digital-hardware hosts, and assigned functions without inventing missing assignments. A design assignment does not by itself prove that the model artifact is installed, reachable, capability-approved, or bound to its host.

## Operating rule: resident AI follows its host

A model assigned to a digital hardware component is integrated with that component's operational lifecycle. While the host is enabled and operational, the model binding and its assigned service remain active/available. Actual inference is scheduled when workload arrives; an idle host must not burn compute by generating tokens continuously.

A model with multiple assignments remains one logical model/runtime identity. Route requests to its assigned functions through the existing function router, scheduler, and compute fabric. Do not register duplicate copies of the same model just to represent multiple functions. Apply bounded concurrency only where overlapping work is actually required and supported by the backend.

The host's deterministic control logic remains authoritative for enable/disable, reset, dispatch gates, resource allocation, safety/policy checks, and status. AI output is not authorization to bypass those controls.

## Model assignment inventory

| Model ID | Confirmed assignment in available project evidence | Unresolved design information | Evidence status |
|---|---|---|---|
| `qwen3` (configured endpoint name `qwen3`) | Primary CPU-intelligence AI for Coreless CPU execution. | Preserve any additional original assignment; exact function/host not recovered in the records inspected for this update. | CPU role is documented; native instruction-execution binding and live trained-model validation remain incomplete. |
| `deepseek` (configured endpoint name `deepseek-r1`) | No exact hardware/function assignment confirmed by the available repository evidence. | Recover the original assignment; do not infer it from the model name. | Capability evaluation pending. |
| `gpt-oss` (configured endpoint name `gpt-oss:20b`) | No exact hardware/function assignment confirmed by the available repository evidence. | Recover the original assignment; do not infer it from the model name. | Capability evaluation pending. |
| `gemma` (configured endpoint name `gemma3`) | No exact hardware/function assignment confirmed by the available repository evidence. | Recover the original assignment and verify whether it is one of the two models with multiple assignments. | Capability evaluation pending. |
| `codestral` (configured endpoint name `codestral`) | No exact hardware/function assignment confirmed by the available repository evidence. | Recover the original assignment; do not infer it from the model name. | Capability evaluation pending. |

The configured endpoint names above are configuration strings, not proof that those exact model artifacts are installed, reachable, or validated. Earlier role suggestions for DeepSeek, GPT-OSS, Gemma, or Codestral are not treated as user-approved assignments unless supported by original design records.

## Digital AI chipset integration

The digital AI chipset must have an AI model integrated with its component lifecycle; the deterministic chipset controller is not itself that model. Keep one canonical chipset/controller instance and use the existing registry, scheduler, and compute fabric rather than creating a second runtime.

The identity of the model assigned as the chipset's resident AI is **unresolved in the repository evidence inspected for this map**. Do not silently infer the identity from a model name or duplicate a model to fill the slot. Recover the original decision before changing runtime bindings. Once assigned, the model remains available while the chipset host is operational, and its requests pass through the same capability/policy gates and resource scheduling as other AI work.

## Assignment and lifecycle invariants

1. **Design intent is not capability approval.** Every enabled route must be backed by evaluation of the exact deployed artifact and a declared capability.
2. **No name-based guessing.** Model IDs do not automatically confer CPU, chipset, GPU, communications, vision, or orchestration roles.
3. **Host lifecycle governs availability.** Host active means the resident binding is available; it does not require continuous inference while idle.
4. **One model identity, multiple declared functions.** Multiple assignments do not require duplicate registrations or model copies.
5. **Route by function.** Dispatch only to enabled models explicitly assigned to the requested function. Fail closed when no eligible assignment exists.
6. **Resource limits are selective.** Establish bounded concurrency only for models with real overlapping assignments/workloads. Do not fan every request out to all models.
7. **Hardware controls remain deterministic.** The chipset/controller and host CPU/VM/policy controls retain authority over dispatch, resource allocation, reset, and fault handling.
8. **Keep evidence honest.** Report intended, implemented, evaluated, and physically validated states separately. Reference tests do not prove trained-model quality or physical hardware operation.

## Next reconciliation gates

1. Recover Qwen3's exact earlier assignment in addition to CPU intelligence.
2. Recover the specific model intended to be resident in the AI chipset.
3. Recover the identities and full function lists of the two models with multiple assignments.
4. Compare those recovered decisions with `ai/function_router.py`, `ai/model_part.py`, and chipset dispatch. Implement only missing bindings and preserve existing assignments.
5. Run per-artifact inference/capability evaluation before enabling routes, then test host lifecycle, fault behavior, and bounded concurrency only for the models that need it.

## Related contracts

- `specification/ai_chipset_integration.md` — controller, motherboard status nets, scheduler/fabric dispatch.
- `specification/ai_function_routing.md` — explicit function declarations and fail-closed routing.
- `specification/model_capability_evaluation.md` — artifact identity and evaluation gates.
- `specification/component_architecture.md` — autonomous component and resident-AI lifecycle.
