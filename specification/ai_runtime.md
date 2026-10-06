# Persistent local AI machine runtime

Coreless owns a persistent AI runtime alongside the operating environment. The runtime registers local model cores, maintains a durable AI session, coordinates multiple cores, and writes its state into the Coreless machine image.

The default local-core set is Qwen3, DeepSeek, GPT-OSS, Gemma, and Codestral. Registration is local and does not contact a model server. Inference is performed only when explicitly requested.

A persistent AI checkpoint contains versioned session state and AI-core descriptors. It does not serialize model weights, credentials, or live network connections. Reopening the same Coreless machine therefore reconstructs the AI control plane while leaving heavyweight model assets as external local runtime resources.

AI results remain analysis data. The collaboration layer can produce a recommendation, but Coreless policy and authorization remain separate and authoritative.


## Native machine resource integration

Persistent local AI cores are registered into the Coreless machine scheduler as
ordinary `ai:<model-id>` compute resources. This makes AI capacity visible to
machine-level allocation and telemetry without granting the AI subsystem
authority over machine state.

A persistent AI workload submitted through the system's AI compute interface is
represented as a normal compute work item with an explicit operation and model
ID. The scheduler selects the requested AI resource with AI preference and no
implicit conventional fallback. The resulting AI analysis is recorded in the
persistent session before the workload returns.

The machine therefore owns resource allocation while the AI runtime owns
session continuity and model coordination. AI output remains data and does not
become authorization merely because it was produced by a local core.

## High-throughput machine dispatch

The machine distributor derives its default worker count from scheduler-reported
eligible capacity rather than the total registered capacity. Explicit model
affinity and operation capability therefore constrain concurrency to resources
that can actually execute each queued work item.

A single work item takes a direct scheduler path and does not create a thread
pool. Multi-item queues use a deque for constant-time admission of pending
work. These optimizations do not alter allocation, fallback, result ordering,
or persistence semantics.
