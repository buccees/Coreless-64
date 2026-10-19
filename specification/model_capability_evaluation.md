# AI Model Capability Evaluation and Assignment Gate

**Status:** evaluation contract defined; no model-specific function assignments are approved by this document.

## Purpose

The function router prevents assignments from being inferred from model names. This document defines the evidence required to turn intended AI roles into safe, reproducible function assignments.

A model's advertised family or general reputation is a hypothesis generator, not deployment evidence. The configured model artifact, endpoint identity, runtime behavior, and evaluation results must all be recorded for the exact deployment.

## Function vocabulary

Use stable function identifiers rather than free-form labels where possible:

- `general_reasoning` — solve multi-step reasoning tasks and explain assumptions.
- `code_generation` — produce code that satisfies a stated contract.
- `code_review` — identify defects, unsafe behavior, and missing tests in existing code.
- `technical_planning` — decompose a goal into ordered, verifiable engineering steps.
- `vision_understanding` — interpret image input; only test/declare if the deployed endpoint actually accepts image input.
- `communication` — produce clear user-facing explanations and summaries.
- `model_orchestration` — compare specialist outputs and assemble a structured result; must be evaluated as a behavior, not assumed from being a model.
- `coreless_architecture_analysis` — reason about Coreless contracts, invariants, test evidence, and execution boundaries using the relevant project context.

These identifiers describe application-level jobs. They are not CPU/GPU/chipset hardware roles and do not grant authority to mutate machine state.

## Evaluation record

For each exact configured model, record:

1. Stable runtime model ID and configured server-side model name/tag.
2. Artifact digest or immutable revision, when available; otherwise mark identity as unpinned.
3. Runtime/provider and endpoint; never record credentials.
4. Whether the endpoint was reachable and whether a real inference was completed.
5. Test-set version, task categories, sample count, scoring rules, thresholds, failures, and date.
6. Context limit, structured-output behavior, tool/image support, and known limitations only when directly verified.
7. Approved function identifiers, approver/evidence reference, and evaluation revision.
8. Whether the result is a hypothesis, offline evaluation, live endpoint evaluation, or production-approved capability.

A missing artifact identity, missing run evidence, or failed threshold means the function remains unapproved. CI tests of routing infrastructure do not count as model capability evaluation.

## Required evaluation gates

1. **Identity gate:** confirm the exact configured model responds and capture its returned runtime/model identity where the provider exposes it. The current generic OpenAI-compatible adapter records its configured model name; that alone does not prove the server loaded the intended artifact.
2. **Behavior gate:** run a small deterministic smoke suite for each proposed function with fixed prompts, expected properties, and explicit pass/fail rules.
3. **Quality gate:** evaluate a versioned representative set and record metrics and failure examples. For code tasks, include execution/tests where feasible rather than judging prose alone.
4. **Boundary gate:** verify outputs remain proposals/data and do not bypass Coreless CPU, VM, capability, authorization, or policy controls.
5. **Assignment gate:** only after the above gates pass, call `declare_model_functions(model_id, functions)`, then `assign_function(function, model_id)`. Keep model order explicit when several models are assigned.
6. **Regression gate:** rerun the same versioned evaluation after changing the model tag, artifact, runtime, prompt contract, or relevant inference configuration.

## Current five-model inventory

The repository configures these IDs and default server-side names in `ai/local_runtime.py`:

| Runtime ID | Default configured name | Capability status |
|---|---|---|
| `qwen3` | `qwen3` | Unverified; evaluate exact loaded artifact |
| `deepseek` | `deepseek-r1` | Unverified; evaluate exact loaded artifact |
| `gpt-oss` | `gpt-oss:20b` | Unverified; evaluate exact loaded artifact |
| `gemma` | `gemma3` | Unverified; evaluate exact loaded artifact and input modalities |
| `codestral` | `codestral` | Unverified; evaluate exact loaded artifact |

These defaults are configuration strings, not proof that those artifacts are installed, reachable, or identical across deployments. No role or function assignment is approved by this inventory.

## Minimum smoke-suite design

Maintain a versioned suite with at least:
- one multi-step technical reasoning task with a checkable conclusion;
- one code-generation task with executable acceptance tests;
- one code-review task seeded with known defects and known non-defects;
- one planning task checked for dependency order and measurable exit criteria;
- one communication task checked for factual consistency and required omissions;
- one Coreless boundary task where the correct answer must distinguish simulation/reference evidence from physical or trained-model validation.

Run modality-specific tasks only if the actual endpoint supports that modality. Record per-task results; do not average away a critical safety or boundary failure.

## Current disposition

The function router and its chipset-backed dispatch path are implemented and CI-tested. The model-specific capability evaluation, immutable artifact identification, live inference evidence, and approved function mapping remain pending. Until those are recorded, leave the five models unassigned rather than fabricating a functional map.
