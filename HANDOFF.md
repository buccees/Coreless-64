# Coreless-64 — Project Handoff

## Current state

**Status: green.** Coreless-64 has a stable reference/conformance foundation and a working 314DNest management/control plane.

The project now has two connected layers:

1. **Coreless-64** — the 64-bit digital computer architecture and execution engine.
2. **314DNest** — the System Fabric and local AI environment that coordinates AI cores with Coreless resources through deterministic interfaces and policy.

Do not treat 314DNest as a remote AI dependency or the Coreless CPU. The CPU, MMU, hypervisor, and architectural protection remain authoritative.

## Coreless-64 completed foundation

- 64-bit architectural model
- variable-length 32/64/128-bit instruction framing
- scalar, memory, branch/jump, system, atomic, vector, matrix, crypto, and VM instruction families
- four privilege levels: USER, SUPERVISOR, HYPERVISOR, MACHINE
- precise traps and retirement behavior
- CSR privilege/read-only enforcement
- R0 hard-wired to zero
- MMU/TLB permission foundations
- interrupts and traps
- vector and matrix architectural state
- multiprocessing foundations
- persistent machine storage
- storage-backed virtual RAM
- graphics/display and networking foundations
- VM isolation and hypervisor lifecycle/state control
- directional VM IPC capabilities
- cross-VM shared-memory capabilities
- VM capability revocation on destruction
- conformance tests and green CI baseline

## 314DNest completed foundation

314DNest coordinates local AI with the Coreless machine through explicit interfaces.

Completed:

- AI-Core registry
- concurrent multi-model coordination
- deterministic collaboration and one group result
- disagreement handling without automatic selection
- dynamic workload distribution
- failover/reassignment when a model fails
- bounded worker scheduling
- cancellation support
- deterministic policy boundary
- explicit capability enforcement
- direct binding to actual Coreless CPU/memory/storage/device controls
- actual Coreless hypervisor VM start/stop control
- telemetry provider
- append-only audit log
- human-AI session layer
- structured terminal command ABI
- confirmation handling for sensitive terminal commands
- optional OpenAI development adapter

Current AI participants are Qwen3, DeepSeek, gpt-oss, Gemma, and Codestral. GPT-5.6 Luna remains an optional external participant through the OpenAI adapter.

### Security/control rule

AI output is never authorization.

Protected flow:

AI result → structured proposal → deterministic policy → capability check → Coreless resource → telemetry/audit

Model identity, VM identity, storage location, physical placement, or natural-language approval cannot substitute for an explicit capability.

## Important files

Coreless execution:
- reference/core.py
- reference/machine_runtime.py
- reference/storage.py
- reference/virtualization.py
- reference/device_io.py

AI/System Fabric:
- ai/interfaces.py
- ai/registry.py
- ai/collaboration.py
- ai/coordinator.py
- ai/work_distribution.py
- ai/policy.py
- ai/resource_control.py
- ai/management.py
- ai/telemetry.py
- ai/audit.py
- ai/session.py
- ai/commands.py
- ai/openai_client.py

Specifications:
- specification/system_fabric.md
- specification/314d_nest.md
- specification/isa.md
- specification/isa_conformance.md

## Local intelligence installation status\n\nThe first local intelligence runtime layer is now in the repository. `ai/local_runtime.py` provides a dependency-free OpenAI-compatible local inference adapter, and `register_default_local_cores()` registers Qwen3, DeepSeek-R1, gpt-oss:20b, Gemma 3, and Codestral with the existing 314DNest registry.\n\n`scripts/install-local-ai.py` creates the local model configuration template. With `--pull`, it can pull the configured models through an installed Ollama runtime. Model weights remain environment/storage content and are never committed to the repository.\n\nThe five local cores are now validated through the common AI-Core interface and a 314DNest end-to-end coordinator test. The repository has since advanced through the machine AI compute fabric, telemetry-aware scheduler, unified machine work distribution, and explicit AI capability advertisement. Live target-environment inference remains blocked until the actual Coreless test environment exists. The next implementation block is the local tensor/Transformer execution layer in parallel with building that test environment.\n\n## Remaining major work

### 1. Coreless test environment

Establish the reproducible environment needed to execute the actual Coreless machine from persistent storage. CI/reference tests are not a substitute for this live environment.

### 2. Local model runtimes

The common local adapter and five-core registration are implemented. Remaining work is live validation and model-specific runtime/weight integration for:

- Qwen3
- DeepSeek
- gpt-oss
- Gemma
- Codestral

All local models should use the common AI-Core interface and remain interchangeable at the collaboration/work-distribution layer.

### 3. Local tensor runtime

Build tensor execution on the existing Coreless vector/matrix foundation. Keep model-runtime details above the architectural CPU boundary.

### 4. Transformer compatibility

Add loading/execution support for compatible locally stored Transformer models through the local tensor runtime.

### 5. Native Coreless operating environment

Continue the machine itself:
- firmware
- boot
- Coreless kernel
- process model
- full memory management
- device drivers
- networking
- GUI
- remote display/input
- application environment

### 6. Scaling and compatibility

Continue dynamic CPU/memory/AI/GPU scaling, large persistent machine images, multiple guest machines, Coreless-native tooling, x86-64/ARM64 compatibility, binary translation, guest OSes, and legacy virtualization.

### 7. Final integration/conformance

After the major runtime layers stabilize, run a final cross-layer audit covering:
- ISA/spec consistency
- VM/capability semantics
- AI policy boundaries
- resource-control behavior
- telemetry/audit behavior
- terminal/session behavior
- model failure and cancellation behavior
- persistent machine-state behavior
- end-to-end Coreless execution.

## Development rules

- Inspect the current repository before changing it.
- Batch related implementation changes.
- Do not trigger unnecessary CI runs while a known batch is still being constructed.
- When a test fails, determine whether the implementation or the test expectation is wrong before changing either.
- Keep architectural rules in specifications and implementation behavior in code.
- Never treat natural-language AI output as an authorization token.
- Never commit API keys or credentials.
- Keep local AI operation independent of the optional OpenAI backend.

## Architectural goal

> **The Coreless computer is the computational architecture carried by persistent storage. The host provides the external interface; it is not the Coreless CPU.**

> **314DNest gives the computer a coordinated local intelligence layer without giving AI authority to bypass deterministic Coreless controls.**

## Resume point

**Current green resume point:** the machine scheduler is telemetry-aware, CorelessMachine exposes unified work distribution, AI resources advertise explicit capabilities, and automated validation is green.

Continue with the **local tensor/Transformer execution layer** while the reproducible Coreless test environment is built in parallel. Do not mark live AI inference complete until the actual Coreless runtime environment has been exercised. Do not rewrite the completed policy, resource-control, collaboration, or Coreless execution foundations unless a concrete failing test or architectural inconsistency requires it.