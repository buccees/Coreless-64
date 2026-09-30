# Coreless

**Coreless is a computer architecture in which the complete digital computer can be carried by persistent storage and executed by a digital Coreless execution engine.**

> **Coreless is the computer. Persistent storage carries the machine state. The Coreless digital execution engine runs the machine. External equipment provides power and I/O.**

Coreless is not intended to be a conventional virtual machine whose CPU, RAM, operating system, or computational AI are supplied by a host.

## Coreless-64

**Coreless-64** is the 64-bit Coreless architecture. It defines CPU execution, virtual memory and protection, privilege and interrupts, multiprocessing, vector and matrix/AI computation, graphics and networking, virtualization and VM isolation, persistent machine state, scalable resources, and compatibility through translation, emulation, guest OSes, and virtualization.

The repository contains the digital reference execution engine that implements these rules.

## Persistent machine

Persistent storage is the authoritative carrier of Coreless machine state, including CPU state, virtual RAM, address-space and process state, operating-system state, filesystem and application state, device/graphics/networking state, virtualization state, boot state, and checkpoints.

Storage-backed virtual RAM is part of the Coreless machine model. Active pages may be cached by an implementation, but persistent machine state belongs to the Coreless machine image.

## Digital execution engine

The current implementation is software, but it is the **Coreless execution mechanism**, not an architectural host dependency.

Persistent Coreless Machine Image → Coreless Digital Execution Engine → Coreless Machine State → persistent machine image.

reference/core.py implements Coreless-64 CPU execution. reference/machine_runtime.py integrates CPU, memory, persistent storage, devices, graphics, networking, and machine state.

## External boundary

The intended external environment provides the interface to Coreless: power/startup, display, keyboard/mouse or other input, and network connectivity.

The external environment is not the computational owner of Coreless.

## 314DNest — System Fabric and local AI

**314DNest** is the codename for the complete system environment that coordinates AI with the Coreless machine.

Coreless AI is a subsystem of the computer, not merely an external chatbot.

The System Fabric connects virtual CPUs and scheduling, virtual RAM and memory management, persistent storage, devices and networking, virtualization, AI cores, AI collaboration, deterministic policy and capabilities, telemetry, and audit.

> **Every component plugs into an interface. Nothing reaches around the interface.**

### Multi-core AI

The local AI architecture is designed so multiple models can work simultaneously and produce one coordinated result.

Current collaboration participants include Qwen3, DeepSeek, gpt-oss, Gemma, and Codestral. The architecture also supports an optional external GPT-5.6 Luna adapter through the OpenAI API. Luna is optional and local operation does not depend on it.

AI cores independently analyze the same context, cross-review results, resolve disagreements, and produce one deterministic group result before any protected action reaches Coreless policy.

AI output is never itself authorization.

### Local model runtime\n\nThe repository now contains a dependency-free local inference adapter and default registration for the five selected local cores. It targets an OpenAI-compatible local model server, so the Coreless AI layer does not require a remote API key for local inference.\n\nThe default local model names are Qwen3, DeepSeek-R1, gpt-oss:20b, Gemma 3, and Codestral; each can be overridden with a CORELESS_*_MODEL environment variable. The setup helper writes the local configuration template and can optionally pull the configured models through an installed Ollama runtime. Model weights are never placed in Git.\n\nUse `python3 scripts/install-local-ai.py` to generate the local configuration template; add `--pull` to install the configured models through Ollama.\n\n### Fault-tolerant AI workload distribution

AI cores are treated as interchangeable workers by default. Work can be dynamically distributed across available cores, and failed work can be reassigned to another healthy core. Model specialties are metadata, not permission boundaries.

### Deterministic management boundary

AI-controlled machine operations pass through explicit capabilities and deterministic policy.

The current management path can bind authorized operations to actual Coreless resources: CPU execution and program loading, virtual memory, persistent storage, network and graphics devices, and VM lifecycle through the Coreless hypervisor.

Unauthorized or capability-free proposals are rejected before reaching those resources.

The management plane also provides telemetry, append-only audit records, human-AI sessions, structured terminal commands, confirmation for sensitive commands, cancellation support, and bounded AI worker scheduling.

Authority levels are OBSERVE, RECOMMEND, ASK, POLICY, and SAFE.

A conversational response is never an authorization token.

## Current status

The reference architecture and execution foundation are substantially implemented and the current CI baseline is green.

### Implemented

- Coreless-64 ISA and variable-length instruction framing
- CPU execution and architectural protection
- MMU/TLB foundations
- interrupts and traps
- vector and matrix execution
- multiprocessing foundations
- persistent machine storage
- storage-backed virtual RAM
- graphics/display and networking foundations
- VM isolation and hypervisor control
- VM IPC and shared-memory capability model
- AI-Core registry
- concurrent 314DNest coordination
- deterministic AI collaboration
- fault-tolerant/dynamic AI work distribution
- deterministic policy and capability enforcement
- direct Coreless resource control
- telemetry
- audit logging
- human-AI sessions
- structured terminal command ABI
- cancellation and bounded AI worker scheduling
- optional OpenAI development adapter

### Next major work

1. Local model runtime adapters for Qwen3, DeepSeek, gpt-oss, Gemma, and Codestral.
2. Local tensor runtime built on the existing vector/matrix execution foundation.
3. Transformer compatibility for supported locally stored models.
4. Native Coreless operating environment: firmware, boot, kernel, processes, drivers, GUI, and applications.
5. Final integration and conformance pass.

## Compatibility

Coreless-native software targets Coreless-64. Existing software can eventually be supported through binary translation, dynamic translation, emulation, guest operating systems, and virtualization. Initial compatibility targets include x86-64 and ARM64.

## Specifications

- Execution Model: specification/execution-model.md
- Digital Execution Engine: specification/computational-fabric.md
- Coreless-64 Architecture: specification/architecture.md
- Registers: specification/registers.md
- ISA: specification/isa.md
- Memory: specification/memory.md
- Privilege: specification/privilege.md
- Interrupts: specification/interrupts.md
- ABI: specification/abi.md
- Devices: specification/devices.md
- Graphics: specification/graphics.md
- Networking: specification/networking.md
- Virtualization: specification/virtualization.md
- System Fabric: specification/system_fabric.md
- 314DNest: specification/314d_nest.md
- Roadmap: ROADMAP.md

## Optional OpenAI development backend

ai/openai_client.py provides an optional OpenAI Responses API adapter. It is a development/integration backend, not a Coreless CPU dependency and not a replacement for local AI.

Configuration uses OPENAI_API_KEY, OPENAI_MODEL, and OPENAI_BASE_URL. Never commit a real API key. Use .env.example.

## Project principles

> **Coreless is the computer.**
> **Persistent storage carries persistent machine state.**
> **The Coreless digital execution engine runs the computer.**
> **AI can assist the machine, but deterministic Coreless controls remain authoritative.**
> **Every subsystem communicates through explicit interfaces and authorization boundaries.**

### Live local inference

The repository includes `scripts/live-inference.py` for validating the actual local model runtime. It does not install weights or store them in Git. With Ollama running and the five configured models installed, run:

```bash
python3 scripts/live-inference.py
```

The runner sends one request through the same `AICoreRegistry` and `NestCoordinator` used by 314DNest, prints each live model response, reports failures independently, and shows the resulting group state. A response is never an authorization token; protected actions remain subject to the deterministic policy boundary.


---

# 🚧 **CORELESS TEST ENVIRONMENT REQUIRED**

**LIVE INFERENCE CANNOT BE RUN YET UNTIL A TEST ENVIRONMENT EXISTS.**

Coreless is currently a software/reference implementation. A tester needs a machine, VM, or other supported persistent-storage environment on which to install and execute Coreless before live local AI inference can be validated.

**Do not treat the repository's CI tests as live Coreless execution.** CI validates the reference implementation; live inference requires an actual Coreless runtime environment with the local AI runtime and model weights available.

### What a tester needs

- Persistent storage for the Coreless environment
- A supported host/boot environment capable of starting the Coreless execution engine
- Display/input/network interfaces as required by the current runtime
- Local AI runtime (currently Ollama/OpenAI-compatible local endpoint)
- The configured local models: Qwen3, DeepSeek, gpt-oss, Gemma, and Codestral
- Python and the Coreless repository

### Live inference test

Once a Coreless test environment exists:

```bash
python3 scripts/live-inference.py
```

The script sends one real request through the five local AI cores and 314DNest, then reports each response, failures, and group state.

**This section is intentionally prominent so a tester can see immediately that live inference requires an actual Coreless test environment.**

See `TESTING.md` for the current test-environment checklist and validation sequence.
