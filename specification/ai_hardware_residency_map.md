# Coreless-64 AI-to-Hardware Residency Map

**Status:** component-scoped AI role boundary baseline. Resident object binding is implemented; exact artifact capability approval, live inference, and physical validation remain separate gates.

## Purpose

This map assigns each configured model a primary place and explicit functions so implementation can proceed without loading every model for every request. These are engineering role assignments, not claims that the deployed artifacts have already passed capability tests.

## Operating rule: resident AI follows its host

A model assigned to a digital hardware component is integrated with that component's operational lifecycle. While the host is enabled and operational, the model binding and assigned service remain active/available. Actual inference is scheduled when workload arrives; an idle host must not burn compute by generating tokens continuously.

A model with multiple assignments remains one logical model/runtime identity. Route requests to its assigned functions through the existing function router, scheduler, and compute fabric. Do not register duplicate copies of the same model just to represent multiple functions. Keep model workloads serialized or bounded unless real overlapping work is necessary and the backend can support it. Do not fan every request out to all models.

The host's deterministic control logic remains authoritative for enable/disable, reset, dispatch gates, resource allocation, safety/policy checks, and status. AI output is not authorization to bypass those controls.

## Assigned model roles

| Model ID / configured endpoint | Assigned host / place | Assigned functions | Multiplicity |
|---|---|---|---|
| `qwen3` | Coreless CPU — primary CPU-intelligence model | Main CPU intelligence for Coreless execution: interpret CPU-level work and provide the primary AI reasoning path for that work. It is not a training coordinator. | One model identity; CPU role is the confirmed baseline. |
| `gpt-oss` / `gpt-oss:20b` | Digital AI chipset — resident chipset AI service | Chipset-facing AI support for interpreting and organizing requests presented to the chipset gate. It does **not** replace the deterministic chipset controller, scheduler, policy checks, or dispatch authorization. | Single assigned role. |
| `deepseek` / `deepseek-r1` | Dedicated reasoning/planning component attached to the CPU-side request path | Deep reasoning and technical planning only, when explicitly routed to this component. It returns results to the requester and never takes over CPU control, chipset control, communication, graphics, or code-generation responsibilities. | Two functions within one component role; one runtime/model identity. |
| `gemma` / `gemma3` | Dedicated communication/input interface component connected to the existing host network-adapter path | Communication-side interpretation and response formulation for traffic handled by this component only. It may interpret incoming interaction context only where that context is part of the communication interface contract. It must not perform general reasoning/planning, chipset control, graphics processing, or code/firmware work. Do not assume vision or other multimodal features until the exact artifact is verified. | One component role with explicitly bounded communication functions; one runtime/model identity. |
| `codestral` | Code/firmware development service | Code generation and code review for Coreless software, firmware, and integration changes. It proposes code; repository checks and deterministic runtime controls decide what is accepted or executed. | Single assigned role. |

### Why these roles are separated

- **Qwen3** remains the primary CPU AI, as already established in the project direction.
- **GPT-OSS** is assigned as the chipset's resident AI model because the chipset needs an integrated model. The deterministic digital chipset remains the control gate; this assignment does not create a second runtime or grant the model hardware authority.
- **DeepSeek-R1** is integrated into the dedicated reasoning/planning component and is limited to its declared reasoning/planning interfaces; it is not the CPU's primary intelligence and cannot assume other component roles.
- **Gemma** is integrated into the communication/input component, including the existing host network-adapter path. Its scope is limited to communication-interface functions; it is not a general-purpose fallback model. Multimodal/vision work is not assumed without verifying the deployed artifact.
- **Codestral** is kept focused on code and firmware tasks.

These assignments establish the design baseline for implementation. If prior project records later surface a more specific user-approved assignment, reconcile it explicitly rather than silently discarding it. In particular, preserve the two multi-function assignments above as single model identities; do not duplicate registrations to represent the second function.

## Lifecycle, routing, and resource rules

1. **Host lifecycle governs availability.** When the host is operational, its resident binding/service is available. This does not mean continuously generating tokens while idle.
2. **One model identity, multiple functions.** DeepSeek and Gemma have multiple declared functions, but each keeps one logical runtime identity.
3. **Function-directed dispatch.** Route a request only to the model assigned to that function; do not run every AI for each request. Fail closed when no eligible assignment exists.
4. **Selective concurrency.** Do not run all models simultaneously. Bound or serialize overlapping DeepSeek/Gemma work according to measured resource limits and actual need; avoid imposing needless concurrency machinery on single-role models.
5. **Chipset control stays deterministic.** GPT-OSS may assist chipset-facing interpretation, but cannot override enable/disable, reset, fault handling, policy, scheduling, or dispatch gates.
6. **Capability approval remains a gate.** A role assignment is not proof that the configured endpoint is installed, reachable, or good enough. Evaluate the exact deployed artifact for each assigned function before enabling that route.
7. **Keep evidence honest.** Report design-assigned, code-bound, artifact-verified, capability-approved, and physically validated states separately.

## Implementation status and next gates

- The repository's configured endpoint strings are `qwen3`, `deepseek-r1`, `gpt-oss:20b`, `gemma3`, and `codestral`. Those strings alone do not prove artifacts are installed, reachable, or validated.
- The digital AI chipset currently has a deterministic software controller integrated into the existing machine runtime; assigning GPT-OSS as its resident AI does not by itself bind or execute the model there.
- Qwen3's native binding to Coreless instruction execution and live trained-model validation remain incomplete.
- Compare this assignment baseline with `ai/function_router.py`, `ai/model_part.py`, the chipset dispatch path, and declared capability contracts. Implement only missing bindings; do not create duplicate model registrations.
- Run per-artifact inference and capability evaluation before enabling each route. Then test host lifecycle, fault behavior, and selective resource limits. No live model evaluation or physical hardware validation is implied by this document update.


## Execution-path wiring contract

The role table above is the intended assignment baseline. The following is the required runtime wiring; it is not yet proof that every route is implemented.

| Execution-path set | Owning virtual component | Assigned AI identity | Dispatch boundary |
|---|---|---|---|
| Coreless CPU intelligence / CPU-level reasoning | CPU component and its bound VM | `qwen3` | CPU component executor -> function router -> registered Qwen3 core; deterministic CPU/VM controls retain execution authority. |
| Digital AI chipset request interpretation | Chipset component | `gpt-oss` | Chipset component AI binding -> function router -> existing chipset controller -> scheduler -> compute fabric -> GPT-OSS resource. The model does not replace the controller. |
| Deep reasoning | CPU-side reasoning service/component | `deepseek` | Named reasoning function -> DeepSeek resource; technical-planning requests use the same model identity and a distinct declared function. |
| Input/context interpretation | Input/interaction component | `gemma` | Named interpretation function -> Gemma resource. |
| Communication-facing response formulation | Input/interaction component | `gemma` | Named communication function -> the same Gemma resource identity, not a second registration. |
| Code generation and code review | Development/firmware service/component | `codestral` | Named code function -> Codestral resource; review and generation remain distinct function routes. |

### Required invariants for wiring

1. Give each component a stable component ID, role, VM ID, and at most one resident model ID for its primary AI binding. If a component legitimately exposes multiple execution-path sets, declare each path explicitly rather than assigning overlapping ownership.
2. **Component-purpose confinement:** a component's resident AI may only receive requests through functions declared for that component's role. A model being registered or capable of answering a request does not authorize another component to use it as a fallback. Cross-component work must be an explicit hub-routed handoff to the owning component, with result provenance preserved.
3. Each execution path must declare its capability, input/output contract, owning component, assigned model ID, and deterministic executor/authorization boundary.
4. Resolve every AI dispatch as **path ID -> owning component -> declared function -> one assigned model identity -> existing registry/scheduler/fabric**. Validate model provenance on return.
4. A request must not fan out to all registered AIs. For a single-owner path, reject ambiguous multi-model assignments instead of silently selecting one. Any deliberate collaboration must be a separately declared pipeline with distinct stages and explicit result handoff.
5. Keep the AI binding available for the lifetime of an operational component, but only schedule inference for actual work. Do not load duplicate model registrations to represent multiple functions.
6. Component fault/isolation, VM shutdown, or disconnect must make its paths unavailable; recovery/rejoin must revalidate the binding before dispatch resumes.
7. Resource limits must be applied at the model/runtime boundary for models with multiple functions. The current chipset-wide busy guard and the coordinator's cross-model thread pool need review together so concurrency is bounded without allowing duplicate or conflicting work.
8. Do not enable the proposed routes until exact model artifacts and each assigned function pass capability checks. A configured endpoint or role-table entry is not runtime proof.

### Wiring gap checklist

- [x] Create an explicit, persisted execution-path registry linking path IDs to component IDs, functions, and a single owner model.
- [x] `CorelessHub.bind_resident_ai_components(registry)` prevalidates and binds every connected AI-declaring component to the already-registered resident model object; it never creates runtimes and rejects conflicting bindings before mutating any component. Execution paths verify object identity before dispatch. VM lifecycle binding and startup validation remain separate.
- [x] Route owned component AI paths through the existing function router/chipset/scheduler/fabric with no fallback or fan-out.
- [ ] Add startup validation for missing components, missing VMs, absent model registrations, duplicate path ownership, and unsupported function declarations.
- [ ] Extend tests to every assigned path and model provenance: reference CI now covers all five simulated resident roles, eight explicit paths, single-model dispatch, and DeepSeek/Gemma multi-function identity reuse. Component fault/disconnect and restart recovery are covered; persisted all-component binding and bounded concurrency remain open.
- [ ] Run the focused test suite and record actual results before marking wiring complete.

## Related contracts

- `specification/ai_chipset_integration.md` — controller, motherboard status nets, scheduler/fabric dispatch.
- `specification/ai_function_routing.md` — explicit function declarations and fail-closed routing.
- `specification/model_capability_evaluation.md` — artifact identity and evaluation gates.
- `specification/component_architecture.md` — autonomous component and resident-AI lifecycle.
