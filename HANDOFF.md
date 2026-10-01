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

## Local intelligence / model-runtime status

The local AI runtime work has advanced substantially beyond the earlier adapter-only stage.

### Qwen3 native runtime

Qwen3 is the first model being taken through the full native-runtime path because it is currently assigned to the Coreless CPU role.

Implemented and green:

- native Qwen3 configuration/model compatibility
- native Qwen3 tokenizer boundary; generic tokenization is not substituted
- Qwen3 attention Q/K normalization
- Qwen3 RoPE handling with position offsets
- Qwen3 tied word-embedding support
- storage-backed safetensors/model-weight loading
- native Qwen3 forward path
- greedy text generation
- native KV-cache generation
- position-aware causal masking for cached decoding
- grouped-query-attention (GQA) KV-cache layout and regression coverage
- official Qwen3-0.6B artifact validation
- managed Qwen3-0.6B artifact acquisition
- immutable artifact revision pinning
- SHA-256 verification of the large model artifact
- atomic .part downloads
- real-artifact integration runner
- real-artifact metadata validation entry point

The latest confirmed GitHub Actions checkpoint is **run #403 — successful/green**.

Important distinction: green CI proves the repository implementation and tests pass. It does **not** by itself prove that the official trained Qwen3-0.6B weights have successfully completed end-to-end inference. That remains an explicit validation milestone.

### Qwen3 real-artifact path

Relevant files include:

- ai/qwen3.py
- ai/qwen3_model.py
- ai/qwen3_loader.py
- ai/qwen3_tokenizer.py
- ai/qwen3_generation.py
- ai/qwen3_artifact.py
- ai/qwen3_real_artifact.py
- ai/test_qwen3.py
- ai/test_qwen3_model.py
- ai/test_qwen3_artifact.py

The official model weights are runtime data and must not be committed to the repository.

The current development path is:

**official trained artifact → Coreless artifact validation → native tokenizer → native Qwen3 runtime → KV-cached generation → real-model execution**

### Model-as-hardware-component architecture

The project direction is NOT to permanently constrain each model to a simplistic fixed Transformer role.

The intended lifecycle is:

**large capable trained model → role-specific training/specialization → careful slimming → Coreless hardware-component integration → continuous user-specific static adaptation**

Specialization must remove only capabilities that are genuinely irrelevant to the component's assigned role. Capabilities that are necessary, optional-but-useful, or required for future compatibility remain available.

Communication with the user is specifically **not** a capability to remove or minimize. Terminal/session/I/O communication remains a first-class component capability.

The model components are intended to behave as specialized computer parts:

- Qwen3 currently assigned as the CPU intelligence component
- GPU intelligence component must retain the breadth required for multiple driver/API compatibility rather than being aggressively minimized
- other AI components can specialize around storage, networking, communication, orchestration, or other machine roles
- each component must retain sufficient general capability to perform its assigned hardware role
- the VM is a containment/nesting environment, not the definition of the component
- final users should not need to manually manage every model file; model acquisition/installation belongs to the Coreless runtime
- development artifacts can remain external and large; deployment components are the optimized local machine parts

The final product should therefore distinguish between the **training artifact** and the **deployed Coreless component**.
## Remaining major work

### 1. Coreless test environment

Establish the reproducible environment needed to execute the actual Coreless machine from persistent storage. CI/reference tests are not a substitute for this live environment.

### 2. Native local model runtimes

Qwen3 is now the first native model-runtime implementation and is the immediate execution target. Do not replace its native tokenizer or architecture with a generic Transformer path.

Remaining model-specific native-runtime work will follow for:

- DeepSeek
- gpt-oss
- Gemma
- Codestral

All local models should still use the common AI-Core interface at the coordination layer while retaining their own native architectures internally.

### 4. Local tensor runtime

Build tensor execution on the existing Coreless vector/matrix foundation. Keep model-runtime details above the architectural CPU boundary.

### 5. Transformer compatibility

Add loading/execution support for compatible locally stored Transformer models through the local tensor runtime.

### 6. Native Coreless operating environment

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

### 7. Scaling and compatibility

Continue dynamic CPU/memory/AI/GPU scaling, large persistent machine images, multiple guest machines, Coreless-native tooling, x86-64/ARM64 compatibility, binary translation, guest OSes, and legacy virtualization.

### 8. Final integration/conformance

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

**Current green resume point: GitHub Actions run #403 — successful.**

The immediate objective is **real trained Qwen3-0.6B execution**, not another synthetic compatibility layer.

Resume in this order:

1. Use the managed Qwen3 artifact path to obtain/validate the official trained artifact.
2. Execute a minimal one-token forward pass through the native Qwen3 runtime.
3. Verify the output shape and numerical/runtime behavior.
4. Run short real generation using the native tokenizer and KV cache.
5. Only after correctness is established, optimize the storage-backed tensor implementation.
6. Then extend the native-runtime architecture to the other model families.
7. Preserve the model-as-specialized-hardware-component architecture throughout.

Do not mark live AI inference complete merely because CI is green. Do not commit large model weights. Do not replace model-native architectures with a generic path just to make integration easier.
