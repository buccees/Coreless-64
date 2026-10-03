# Coreless-64 — Project Handoff

## Current state

**Status: green.** The repository is at a stable checkpoint with the Coreless-64 digital machine foundation, 314DNest control plane, persistent tensor runtime, and Transformer-to-tensor-runtime integration all passing CI.

Latest confirmed GitHub Actions checkpoint:

**Run #423 — successful/green**

Latest commit:

`aabd6c177d902b836aad85bda399a73df9fbd659` — **Complete Transformer tensor-runtime routing boundary**

The project has two connected layers:

1. **Coreless-64** — the 64-bit digital computer architecture and execution engine.
2. **314DNest** — the local System Fabric that coordinates AI cores with Coreless resources through deterministic interfaces and policy.

314DNest is not the Coreless CPU and is not a remote AI dependency. CPU, MMU, hypervisor, and architectural protection remain authoritative.

## Autonomous component architecture

Coreless now explicitly treats **autonomous, specialized, composable components** as a first-class architectural requirement.

A component is intended to be a complete Coreless computer unit, not merely a peripheral. Its integrated boundary includes:

- Coreless execution
- local memory/storage
- VM isolation
- local AI runtime/model
- role specialization
- persistent identity
- capability advertisement
- component communication/discovery
- health and fault isolation

A component must be able to operate independently.

A Coreless Hub is the composition boundary. It discovers components, records their identities and capabilities, connects/disconnects them, and aggregates their capabilities into a unified composition.

The intended lifecycle is:

**component → standalone operation**

and:

**component A + component B + component C → Coreless Hub → unified Coreless computer**

Connecting components does not turn them into passive peripherals. Each component retains its own identity, specialization, AI, VM, and execution boundary.

Per-component AI is intentional. A component can carry a role-specific model and use its VM as the controlled environment for training, adaptation, evaluation, and model updates. AI remains subject to deterministic Coreless CPU, VM, capability, and policy controls.

The first software boundary is now implemented in:

- `reference/components.py`
- `reference/test_components.py`
- `specification/component_architecture.md`

This initial layer deliberately establishes identity, specialization, standalone state, hub discovery, connect/disconnect, and capability composition before introducing shared live execution state.

## Coreless-64 completed foundation

- 64-bit architectural model
- variable-length 32/64/128-bit instruction framing
- scalar, memory, branch/jump, system, atomic, vector, matrix, crypto, and VM instruction families
- USER, SUPERVISOR, HYPERVISOR, and MACHINE privilege levels
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
- directional VM IPC
- cross-VM shared-memory capabilities
- VM capability revocation on destruction
- conformance tests and green CI baseline

## Coreless system lifecycle

The reference machine now has a complete digital lifecycle layer through `reference/system.py`.

`CorelessSystem` provides:

- persistent boot manifest
- boot
- run
- native Coreless shell command routing
- checkpoint
- restore
- shutdown
- persistent machine status/state handling

The reference OS/process/memory-management lifecycle is represented in the repository and covered by tests.

## 314DNest completed foundation

Completed:

- AI-Core registry
- concurrent multi-model coordination
- deterministic collaboration and group results
- disagreement handling without automatic selection
- dynamic workload distribution
- failover/reassignment
- bounded worker scheduling
- cancellation
- deterministic policy boundary
- explicit capability enforcement
- direct binding to Coreless CPU/memory/storage/device controls
- Coreless hypervisor VM start/stop control
- telemetry provider
- append-only audit log
- human-AI session layer
- structured terminal command ABI
- confirmation handling for sensitive terminal commands
- optional OpenAI development adapter

Current local AI participants include Qwen3, DeepSeek, gpt-oss, Gemma, and Codestral. GPT-5.6 Luna remains optional through the OpenAI adapter.

### Security/control rule

**AI output is never authorization.**

Protected flow:

**AI result → structured proposal → deterministic policy → capability check → Coreless resource → telemetry/audit**

Natural-language approval, model identity, VM identity, or storage location cannot substitute for an explicit capability.

## Tensor runtime — current checkpoint

The persistent tensor runtime is now bound to the Coreless machine and its vector/matrix execution foundation.

Relevant files:

- `ai/tensor.py`
- `ai/tensor_runtime.py`
- `reference/core.py`
- `reference/machine_runtime.py`

Implemented:

- dtype-aware tensor creation
- fp16/bf16/fp32/fp64 and int8/int16/int32/int64 semantic dtypes
- persistent tensor state
- Coreless CPU binding
- native vector add
- native vector multiply
- deterministic vector dot using native vector multiplication plus deterministic reduction
- native integer matrix multiplication for supported architectural shapes
- automatic routing of supported integer matrix multiplication through the Coreless matrix unit
- generic fallback for unsupported shapes/dtypes
- FP32 vector execution coverage
- tensor persistence across machine reopen

Important limitation: the current Tensor object still stores values as Python numeric tuples while dtype remains a semantic/storage label at the runtime boundary. Do not describe this as true hardware-format storage yet.

## Transformer integration — current checkpoint

Transformer execution is now routed through the persistent Coreless tensor runtime.

Implemented:

- dtype-preserving embedding
- RMS normalization
- scaled dot-product attention through the runtime when supplied
- feed-forward matrix operations through the runtime
- Transformer-layer residual and matrix operations through the runtime
- final language-model head routing through the runtime
- explicit regression test proving matrix multiplication calls cross the TensorRuntime boundary

Latest CI run #423 confirms this integration is green.

This is the current resume point before deeper native architectural execution work.

## Qwen3 native runtime

Qwen3 remains the first model being taken through the full native-runtime path because it is currently assigned to the Coreless CPU role.

Implemented and green:

- native Qwen3 configuration/model compatibility
- native Qwen3 tokenizer boundary
- Q/K normalization
- RoPE with position offsets
- tied word embeddings
- storage-backed safetensors/model-weight loading
- native Qwen3 forward path
- greedy text generation
- native KV-cache generation
- cached causal masking
- grouped-query-attention KV-cache layout and regression coverage
- official Qwen3-0.6B artifact validation
- managed artifact acquisition
- immutable artifact revision pinning
- SHA-256 verification
- atomic `.part` downloads
- real-artifact integration runner
- metadata validation entry point

**Important:** green CI does not prove that the official trained Qwen3-0.6B weights have completed successful end-to-end inference. That remains a separate validation milestone.

### Qwen3 real-artifact validation issue to revisit

The official Qwen3-0.6B artifact was downloaded to the Lubuntu development VM and all required files were present. A manual SHA-256 check produced:

`f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b`

The extra trailing `b` means the downloaded `model.safetensors` did **not** match the pinned Coreless SHA-256:

`f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874`

The mismatched weights were removed during troubleshooting, and restoring the exact pinned artifact was not completed. The Hugging Face/native numerical reference comparison was therefore **deferred**.

**Do not spend development time on this now.** Revisit after the native Coreless execution boundary and remaining implementation work are complete. At that point, reacquire/validate the exact pinned Qwen3 artifact and perform the real forward/reference validation.

Do not commit large model weights.

## Model-as-hardware-component architecture

The intended lifecycle remains:

**large capable trained model → role-specific specialization → careful slimming → Coreless hardware-component integration → continuous user-specific static adaptation**

The model component must retain the capabilities necessary for its assigned hardware role. The VM is a containment/nesting environment, not the definition of the component.

Qwen3 is currently assigned to the CPU intelligence role. Future model components can specialize around GPU, storage, networking, communication, orchestration, or other machine roles.

## Remaining major work

### 1. Native Coreless execution boundary

This is the immediate next engineering target.

Continue from the green Transformer/tensor-runtime checkpoint and deepen the stable boundary between model tensor operations and Coreless architectural vector/matrix execution.

Priority:

1. inspect and stabilize the public Coreless vector/matrix execution API
2. avoid unnecessary dependence on private execution helpers
3. route supported Transformer tensor operations through the stable native boundary
4. add focused regression tests
5. batch related changes before CI

### 3. Real trained Qwen3-0.6B execution

After the native execution boundary is stable:

1. obtain/validate the official trained artifact through the managed artifact path
2. execute a minimal real one-token forward pass
3. verify output shape and numerical/runtime behavior
4. run short real generation using the native tokenizer and KV cache
5. optimize only after correctness is established

Do not mark live AI inference complete merely because CI is green.

### 4. Additional native model runtimes

Extend the native-runtime architecture to:

- DeepSeek
- gpt-oss
- Gemma
- Codestral

Each model should retain its native architecture internally while using the common AI-Core coordination interface.

### 5. Native Coreless operating environment

Continue:

- device drivers
- networking
- GUI
- remote display/input
- application environment

### 6. Scaling and compatibility

Continue:

- dynamic CPU/memory/AI/GPU scaling
- large persistent machine images
- multiple guest machines
- Coreless-native tooling
- x86-64 compatibility
- ARM64 compatibility
- binary translation
- guest OSes
- legacy virtualization

### 7. Final integration/conformance

Perform a final cross-layer audit covering:

- ISA/spec consistency
- vector/matrix encoding and execution semantics
- VM/capability semantics
- AI policy boundaries
- resource-control behavior
- telemetry/audit behavior
- terminal/session behavior
- model failure/cancellation behavior
- persistent machine state
- end-to-end Coreless execution

## Development rules

- Inspect the current repository before changing it.
- Batch related implementation changes.
- Do not trigger unnecessary CI runs while a known batch is still being constructed.
- When a test fails, determine whether the implementation or the test expectation is wrong before changing either.
- Keep architectural rules in specifications and implementation behavior in code.
- Never treat natural-language AI output as an authorization token.
- Never commit API keys or credentials.
- Keep local AI operation independent of the optional OpenAI backend.
- Do not substitute generic model implementations for native model architectures merely to make integration easier.
- Defer optional external-reference validation until the native implementation milestone is ready.

## Architectural goal

> **The Coreless computer is the computational architecture carried by persistent storage. The host provides the external interface; it is not the Coreless CPU.**

> **314DNest gives the computer a coordinated local intelligence layer without giving AI authority to bypass deterministic Coreless controls.**

## Resume point

Continue the **native Coreless execution boundary** and the new **autonomous component/hub architecture** in parallel.

**Green resume point: GitHub Actions run #423 — successful.**

Latest commit:

`aabd6c177d902b836aad85bda399a73df9fbd659`

**Next session:** continue the **native Coreless execution boundary**, then proceed to real trained Qwen3-0.6B execution.

Do not restart from the older Qwen3-only handoff. The tensor runtime and Transformer routing work described above is already in `main`.

**Do not commit large model weights. Do not claim end-to-end trained-model inference until it has actually been executed and validated.**
