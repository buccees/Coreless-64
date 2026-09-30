# Coreless-64 — Project Handoff

## Current stop point

**Date:** 2026-09-29  
**Current state:** Coreless-64 reference/conformance work is at a confirmed green milestone after the recent ISA, privilege, VM isolation, hypervisor state-control, and OP_VM batches.

**Important:** Do not start by piling changes onto a failing CI run. Inspect the current repository state first, make coherent batches, and run CI only after the batch is internally consistent.

## Major work completed

### ISA / encoding

- Coreless-64 is explicitly a **64-bit architecture**.
- The base instruction form is 32-bit, with variable-length 32/64/128-bit instruction framing.
- Instruction length is determined from the first 32-bit word.
- Base scalar, memory, branch/jump, system, atomic, vector, matrix, crypto, and VM opcode families are represented in the reference encoding.
- Extended instruction framing and rejection of reserved/unsupported forms are covered by conformance tests.

Relevant files:
- `reference/encoding.py`
- `reference/test_encoding.py`
- `specification/encoding.md`
- `specification/isa.md`

### CPU protection and architectural state

The reference CPU now has explicit:
- four privilege levels: USER, SUPERVISOR, HYPERVISOR, MACHINE;
- precise traps and retirement behavior;
- CSR access/privilege checks;
- read-only CSR protection;
- R0 hard-wired to zero;
- MMU/TLB translation and permission checks;
- deterministic reset behavior;
- CPU identity/count and architectural counters;
- vector and matrix architectural state;
- interrupt/trap state.

Important CSR rule:
- writing a read-only CSR -> `illegal_csr`;
- accessing a CSR below its required privilege -> `privilege_violation`.

Relevant file:
- `reference/core.py`

### VM isolation and communication

The virtualization reference model now establishes the core isolation rule:

> Sharing the same Coreless storage device does **not** grant communication or access permission.

By default:
- VM memory is private;
- VM registers/state are private;
- VM devices are private;
- execution state is isolated by VMID.

Communication rules:
- vCPUs inside one VM may exchange messages through that VM's IPC queues;
- VM-to-VM messaging requires an explicit hypervisor-issued **directional IPC capability**;
- capabilities are opaque/revocable;
- cross-VM shared memory requires an explicit owner, target, region, and permission grant;
- VMID, storage location, or physical placement never constitutes authorization;
- destroying a VM revokes its IPC/shared-memory grants;
- unauthorized communication must not modify destination state and is rejected at the virtualization boundary.

Relevant files:
- `reference/virtualization.py`
- `reference/test_virtualization.py`
- `specification/isa.md`

### Hypervisor state control

The reference hypervisor provides:
- VM creation/destruction;
- explicit vCPU allocation bounds;
- VM start/stop;
- isolated interrupt injection;
- per-vCPU state save/restore;
- register-file validation;
- R0 enforcement during state restore;
- IPC/shared-memory grant cleanup on VM destruction.

vCPU state currently includes:
- register file;
- PC;
- SP;
- privilege;
- halted state;
- IPC inbox.

Relevant file:
- `reference/virtualization.py`

### OP_VM milestone

**OP_VM is now an actual Coreless-64 instruction family.**

Defined operations:
- `VM_SEND`
- `VM_RECV`
- `VM_GRANT`
- `VM_REVOKE`
- `VM_SHARE`
- `VM_UNSHARE`

Encoding:
- standard 32-bit R-format fields;
- primary opcode `OP_VM = 12`;
- low five bits select the VM operation.

Execution contract:
- VM instructions require HYPERVISOR privilege;
- VM instructions require a connected hypervisor control interface;
- otherwise they take a `virtualization_fault`;
- a faulting VM instruction does not retire;
- successful handler results may be written to `rd`;
- guest code cannot bypass VM isolation by directly addressing another VM's state.

Reference execution path:
`instruction decode -> CorelessCPU VM dispatch -> vm_handler -> hypervisor-controlled operation`

Relevant files:
- `reference/encoding.py`
- `reference/core.py`
- `reference/test_virtualization.py`
- `specification/isa.md`
- `specification/isa_conformance.md`

Recent commits implementing this milestone:
- `3331761` — concrete VM instruction encoding
- `ef7ee5e` — VM instructions routed through hypervisor control
- `ea69620` — concrete VM instruction conformance
- `b310ff5` — concrete VM control instruction specification

### Conformance discipline

The project now explicitly follows:
1. spec first;
2. implementation contract second;
3. tests third;
4. distinguish API errors from architectural traps;
5. distinguish reserved encodings from unsupported valid operations;
6. keep decoder framing separate from execution semantics;
7. verify precise retirement/state preservation;
8. add every architectural batch to the conformance matrix.

Relevant file:
- `specification/isa_conformance.md`

## What is still provisional

The current virtualization model is a **reference/conformance baseline**, not a finished production hypervisor.

In particular, the next architectural work should make the OP_VM path perform real hypervisor operations rather than only dispatch through a generic handler. The instruction operands/descriptor ABI must be frozen so each VM operation has unambiguous architectural semantics.

The reference VM model also still needs a stronger architectural representation of:
- capability ownership/handle semantics;
- IPC queue limits and backpressure;
- VM event/interrupt notification;
- shared-memory mapping into guest address spaces;
- atomic synchronization across VMs/vCPUs;
- hypervisor resource accounting;
- complete VM context state where additional architectural state is introduced.

## Next implementation order

1. **Freeze the OP_VM operand/descriptor ABI.**
2. Connect each OP_VM operation to the existing hypervisor capability/IPC/shared-memory model.
3. Define exact success/fault results and retirement behavior for each VM instruction.
4. Add negative tests for stale, revoked, wrong-direction, and unauthorized capabilities.
5. Add VM event/interrupt notification semantics.
6. Define shared-memory mapping semantics through the MMU rather than treating a region ID alone as the complete mapping.
7. Extend context save/restore as new architectural state becomes exposed.
8. Update the ISA conformance matrix for every new architectural contract.
9. Only after virtualization is stable, continue the broader ISA freeze checklist and native OS/userspace path.

## Other existing roadmap items

These remain important but should not be mixed into a virtualization fix unless required:
- finish full multi-level page-table/MMU implementation;
- complete the architectural USER -> SUPERVISOR syscall/trap path;
- preserve/restore complete process CPU + MMU state;
- boot and launch native PID 1 / `/init`;
- build minimal native userspace;
- expand filesystem, networking, graphics, scheduler, and application compatibility;
- preserve legacy interoperability through the documented x86-64/ARM64 translation/emulation compatibility layer.

## Repository placement rule

Keep each architectural fact in the layer where it belongs:
- **encoding** -> binary fields, opcode numbers, decode/encode rules;
- **core** -> CPU execution, privilege, traps, retirement, architectural state;
- **virtualization** -> VM lifecycle, capabilities, IPC, shared memory, hypervisor state;
- **tests** -> executable conformance for the exact contracts;
- **specification/isa.md** -> normative ISA behavior and semantics;
- **specification/isa_conformance.md** -> implementation/conformance coverage matrix;
- **HANDOFF.md** -> current state, completed milestones, exact next steps.

Do not duplicate implementation logic into the specification or turn HANDOFF into a second specification.

## CI discipline

When a failure occurs:
1. inspect the failing test and implementation together;
2. determine whether the failure is implementation behavior or an incorrect test expectation;
3. fix the contract/test mismatch before adding more work;
4. batch related fixes;
5. run CI only when the batch is ready.

The project has had several failures caused by incorrect test expectations, so this distinction is now an explicit workflow requirement.

## Coreless architectural goal

Keep the project aligned with the original concept:

> The Coreless computer is the computational architecture carried by persistent storage. The host provides the external interface; it is not the Coreless CPU.

The reference implementation is a digital, hardware-shaped architectural model. It is not itself a claim that the host processor is the Coreless CPU.

**Resume from the OP_VM ABI/semantics freeze.**


## Coreless Intelligence Layer

The long-term architecture includes a **local Coreless Intelligence Layer**. This is not a remote AI dependency and is not merely an application running on top of the CPU. Its purpose is to provide local AI-assisted management and optimization of the Coreless computer while preserving deterministic architectural control.

Architectural principle:
- the Coreless CPU remains responsible for deterministic instruction execution, privilege enforcement, memory protection, traps, VM isolation, and other operations that require exact architectural behavior;
- the local AI engine may assist with scheduling, resource allocation, workload placement, memory/storage management, anomaly detection, optimization, and other explicitly permitted management functions;
- AI requests must pass through a deterministic policy/control boundary before privileged state is changed;
- the AI must not receive unrestricted authority to modify machine, hypervisor, memory-protection, or security state;
- local models and their runtime are intended to reside within the Coreless persistent computational environment, so normal operation does not depend on a remote AI service.

### Local AI roadmap

1. Define the AI-to-Coreless control interface and privilege boundary.
2. Define AI access to scheduler, VM, memory, storage, and resource-management operations.
3. Define model storage/loading and local tensor execution requirements.
4. Build the local AI/tensor runtime around the existing vector and matrix ISA.
5. Add a Transformers compatibility layer for locally stored compatible models.
6. Add controlled AI-assisted system management.
7. Define observability, resource limits, fallback behavior, and deterministic policy enforcement.

The AI engine is an architectural subsystem target, not a replacement for the Coreless CPU and not a remote execution requirement.


## Human-AI terminal management interface

The local intelligence subsystem is intended to be directly accessible through a **Coreless terminal management interface**, modeled on the interactive terminal experience already used by the project's MistralUX work.

This is a first-class Coreless management plane, not merely a chatbot application.

Target interaction flow:

```
USER
  |
  v
Coreless terminal / AI console
  |
  v
Local AI dialogue/session
  |
  v
AI management/control interface
  |
  v
Deterministic Coreless policy boundary
  |
  +--> scheduler
  +--> VM/hypervisor management
  +--> CPU/vCPU resources
  +--> memory / virtual RAM
  +--> persistent storage
  +--> devices / networking
  +--> AI/tensor resources
  |
  v
telemetry / results
  |
  +--> Local AI
  +--> USER
```

The terminal should allow the user to communicate with the local AI conversationally while also exposing the functional management surface of the Coreless environment.

The local AI may:
- inspect system and workload telemetry exposed through the management interface;
- explain current resource usage and system conditions;
- answer questions about VMs, CPUs, memory, storage, devices, workloads, and AI resources;
- propose configuration or resource-management changes;
- execute changes that are explicitly permitted by the active policy;
- ask the user for a decision when a management choice is ambiguous or requires approval;
- retain explicitly configured management preferences and policies;
- report the result of accepted management actions.

The user may issue natural-language management requests such as:
- prioritize a workload;
- preserve or reduce a VM's allocation;
- change an allowed resource limit;
- inspect memory or storage pressure;
- ask why performance has changed;
- request the AI to optimize an allowed subsystem;
- ask what the AI recommends before applying a change.

### Management authority levels

The management interface should distinguish at least:
- **OBSERVE** — AI can inspect permitted telemetry but cannot change state;
- **RECOMMEND** — AI can propose actions but cannot apply them;
- **ASK** — AI must obtain user approval for configured classes of changes;
- **POLICY** — AI may automatically perform actions already authorized by an explicit policy;
- **SAFE** — the deterministic Coreless control layer can force a safe state independently of AI decisions.

A conversational response is never itself an authorization token. Every state-changing operation must pass through the deterministic management/policy boundary and the applicable CPU, MMU, hypervisor, capability, and privilege checks.

### Terminal/session requirements

The future implementation should provide:
- a local interactive terminal command or shell entry point for AI communication;
- persistent dialogue/session context within defined resource limits;
- structured commands alongside natural-language requests;
- machine-readable action proposals and results behind the human-readable conversation;
- explicit confirmation for actions governed by ASK policy;
- policy inspection and configuration;
- audit records for AI proposals, user decisions, policy-authorized actions, and resulting state changes;
- a way for the user to interrupt or cancel an AI management operation;
- clear indication of whether a response is informational, a recommendation, a pending approval, or an executed action.

The terminal is an interface to the Coreless management plane. It must not become a privileged bypass around the architecture.

### Reference implementation direction

The first implementation should mirror the proven interactive MistralUX/Termux pattern at the **experience and control-session level**, while adapting the backend to Coreless-native telemetry, policies, VM/resource controls, and local model execution.

The MistralUX implementation should be inspected when its repository is available to the Coreless development workflow; its interface patterns should inform the Coreless terminal without making MistralUX an execution dependency.

### Next steps for the Human-AI plane

1. Define the terminal command/session ABI.
2. Define the structured AI action/proposal format.
3. Define telemetry exposed to the local AI.
4. Define OBSERVE/RECOMMEND/ASK/POLICY/SAFE authorization semantics.
5. Define persistent management-policy storage.
6. Define audit/event records and cancellation semantics.
7. Implement the terminal/session reference layer.
8. Connect approved operations to scheduler, VM, memory, storage, device, and AI-resource controls.
9. Add conformance tests for authorization, rejection, approval, cancellation, and audit behavior.
10. Integrate the local model/tensor runtime and Transformers compatibility layer after the management boundary is stable.


## Optional OpenAI development adapter

An optional OpenAI Responses API adapter has now been added under `ai/openai_client.py`.

This adapter is an **external/development backend**, not a replacement for the planned local Coreless Intelligence Layer. It exists so Coreless can communicate with an OpenAI model during development and can later be used as one backend behind the Human-AI terminal interface if explicitly configured.

Security requirements:
- API credentials are read from `OPENAI_API_KEY`;
- real credentials must never be committed to the repository;
- `.env` and local credential files are ignored by Git;
- `.env.example` documents the configuration shape;
- the CPU, ISA, hypervisor, and deterministic policy boundary do not depend on the OpenAI service;
- local AI remains the target for normal self-contained Coreless operation.

Current default API model configuration is `gpt-5.6-luna`; it is configurable through `OPENAI_MODEL`.

Relevant files:
- `ai/openai_client.py`
- `.env.example`
- `.gitignore`
- `reference/test_openai_client.py`

The adapter uses the OpenAI Responses API directly through Python's standard library, so adding this optional backend does not add a mandatory third-party Python dependency.
