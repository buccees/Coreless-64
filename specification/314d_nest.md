# 314DNest

## Status

Architecture codename for the Coreless-64 AI-hosting environment.

## Definition

**314DNest** is the architecture that houses, coordinates, and connects AI intelligence to the complete Coreless-64 system.

It is broader than an AI model runtime. The AI can use the permitted resources of the computer through the Coreless System Fabric: compute, memory, persistent storage, I/O, networking, virtualization, project state, and other AI cores.

## AI cores

An AI core is any model/runtime participating through the AI-Core interface. Initial participants may include:

- Qwen3
- DeepSeek
- gpt-oss
- Gemma
- Codestral
- GPT-5.6 Luna through the OpenAI gateway

The architecture does not require any one model. Cores can be added, removed, replaced, or unavailable without changing the surrounding Coreless interfaces.

## Multi-core intelligence

314DNest treats participating models as a coordinated set rather than unrelated chatbots:

1. distribute the task/context;
2. collect independent analyses;
3. exchange relevant analyses and challenges;
4. identify agreement and disagreement;
5. revise or reconcile proposals;
6. produce one structured group result;
7. pass proposed system actions through the deterministic Policy interface.

The group result is an AI result, not automatic machine authority.

## Luna integration

GPT-5.6 Luna is an optional external participant. Its adapter uses the OpenAI API and credentials supplied outside the repository. Luna communicates with 314DNest through the same AI-Core and Collaboration contracts used by local models.

If the API key, network, or external service is unavailable, local 314DNest operation continues.

## Resource ownership

314DNest does not implicitly own CPU, memory, storage, devices, or privileged state. It requests resources through the corresponding Coreless interfaces and receives only the capabilities granted by policy.

## Security rule

No AI model may bypass the System Fabric, hypervisor isolation, MMU protection, capability checks, or Policy interface merely because it is participating in 314DNest.
