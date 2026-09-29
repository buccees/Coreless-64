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
