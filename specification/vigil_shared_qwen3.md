# VIGIL Shared Qwen3 Integration Contract

## Decision

VIGIL is a lightweight Coreless service layer and does **not** package, load, host, fine-tune, or duplicate its own AI model. It uses the already-registered Qwen3 processor/AI runtime owned by Coreless-64 through the existing AI-Core registry, scheduler, TensorRuntime/model adapter, and policy-controlled request interface.

The target is one Qwen3 runtime serving multiple authorized clients, including VIGIL. This is shared inference, not a second copy of Qwen3 dedicated to VIGIL. Reuse the live registered runtime and its machine-bound resources; do not initialize a second model instance just because VIGIL starts.

## Responsibilities

### Coreless-64 / Qwen3 processor

- Owns Qwen3 model loading, model identity, inference lifecycle, memory, execution, scheduling, cancellation, and health.
- Exposes a typed request/result boundary through the existing AI-Core coordination interface.
- Applies the existing capability and deterministic policy checks before any protected resource operation.
- Remains useful to other Coreless services; VIGIL does not own or shut down the shared processor.
- Reports unavailable, busy, cancelled, or failed states explicitly.

### VIGIL spatial service

- Owns blueprint ingestion/normalization, coordinate frames and calibrated transforms, deterministic pose/geometry calculations, spatial queries, confidence bookkeeping, and presentation.
- Uses Qwen3 for language-oriented tasks such as interpreting a user's spatial question, mapping natural language to a bounded typed query, summarizing observations, and explaining a result.
- Sends compact, structured context to Qwen3 rather than raw image/model payloads on every query.
- Has no private model weights, private inference runtime, independent model lifecycle, or hidden AI fallback.
- Does not use model-generated text as a coordinate, confidence score, calibration, or authorization unless a separate deterministic validator independently verifies the relevant typed result.

## Request path

1. Blueprint adapters create a validated, versioned model revision.
2. Sensor adapters emit timestamped observations through the Coreless input/event boundary.
3. Deterministic spatial code estimates pose, uncertainty, and provenance.
4. A VIGIL request is expressed as a typed task with a bounded payload and the registered Qwen3 model/component identity.
5. Coreless capability/policy checks and the existing scheduler dispatch the request to the shared Qwen3 runtime.
6. Qwen3 returns a result tagged with request ID, model identity/revision, status, and provenance where available.
7. VIGIL validates the response schema and uses it only for its permitted interpretation/presentation task.
8. A Qwen3 timeout, refusal, cancellation, or malformed response degrades the conversational interpretation only; raw input, deterministic tracking, and Coreless operation continue.

## Typed request contract

Use repository-native request types where available rather than creating a parallel AI API. The conceptual request fields are:

- `request_id`: unique correlation ID
- `client_component_id`: registered VIGIL service identity
- `task_kind`: bounded enum, e.g. `INTERPRET_SPATIAL_QUERY`, `SUMMARIZE_STATUS`, `EXPLAIN_RESULT`
- `model_binding`: the registered Qwen3 processor identity/revision; no implicit model download or startup
- `context`: bounded structured data, such as model ID/revision, level/zone, pose status, uncertainty, timestamps, and allowed feature labels
- `deadline` / cancellation handle: follow existing scheduler conventions
- `policy/capability context`: derived from Coreless component identity, not from natural-language text

The result should contain:

- matching `request_id`
- actual model/component identity used
- explicit success/error/cancelled/unavailable status
- typed payload or bounded explanatory text
- validation/provenance metadata supported by the runtime

These fields describe the intended contract. Before implementation, inspect and reuse the concrete request, identity, scheduler, and cancellation types already present in Coreless-64.

## Performance and footprint rules

- Do not add a VIGIL-specific copy of Qwen3 weights or a second model server.
- Do not add another tokenizer/model-loading path if the registered Qwen3 adapter already provides one.
- Do not pass full blueprint files or continuous sensor streams into the language model; perform geometric processing locally and send compact task context only.
- Cache deterministic blueprint normalization, coordinate transforms, and repeatable spatial query results with explicit model-revision keys.
- Use bounded queues, deadlines, cancellation, and request coalescing where supported by the existing scheduler.
- Treat inference as optional assistance: geometry and pose tracking must still operate without Qwen3.
- Do not claim zero overhead: shared inference has scheduling and serialization cost, but it avoids a duplicate model/runtime footprint.

## Isolation and security

- VIGIL is a client of Qwen3, not the owner of Qwen3 or a privileged route around Coreless policy.
- Every request is bound to a registered component identity and checked against the existing capability model.
- Prompt text, inferred intent, and Qwen3 output are data, never authorization.
- Spatial actions affecting protected devices require deterministic policy and explicit capabilities independently of model output.
- Keep raw Coreless input delivery operational if VIGIL parsing or Qwen3 inference fails.

## Acceptance tests

1. Starting VIGIL does not load or allocate a second Qwen3 model instance.
2. VIGIL requests route to the already-registered Qwen3 identity through the existing AI-Core/scheduler boundary.
3. Requests preserve correlation IDs, model identity, cancellation, deadlines, and explicit failure status.
4. Unauthorized component requests are rejected by Coreless policy.
5. Qwen3 unavailable/busy/timeout/malformed response cases do not interrupt raw input or deterministic spatial calculations.
6. VIGIL can answer basic coordinate/geometry queries with the model disabled.
7. Natural-language spatial queries become bounded typed operations; Qwen3 does not invent pose values or override calibration.
8. Tests use a fake registered AI-Core; live trained-model inference and physical sensor accuracy are separate validation gates.

## Implementation checkpoint

This document is an architecture contract, not proof that the runtime wiring or acceptance tests have already been implemented. The next code change should inspect existing AI-Core request and scheduler types, then add the thinnest VIGIL adapter plus tests that prove runtime reuse and failure isolation.
