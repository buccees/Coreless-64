# Function-based AI model routing

**Status:** implementation added to the persistent AI runtime; model-specific functional assignments must be explicitly configured and validated for the deployment.

## Contract

- Model identity and model function are separate concepts. A registered model does not become the default for a function merely because of its name.
- A deployment explicitly assigns one or more registered models to a function such as code generation, code review, general reasoning, image understanding, or user communication. These examples are function labels, not pre-filled assignments.
- Assignments preserve declaration order. Multiple models may serve one function; this supports controlled collaboration or ordered fallback decisions without silently changing the chosen function.
- Routing considers only assigned models that are currently enabled. An unassigned function or a function with no enabled assigned models fails closed rather than dispatching to an arbitrary model.
- Assignments are persisted under `ai/function-routing`, restored with the persistent AI runtime, and exposed through runtime status.
- `PersistentAIRuntime.analyze_for_function(function, text, ...)` sends the request only to models explicitly assigned to that function, using the existing coordinator, registry, session, and persistence path.
- Function assignment is metadata/configuration, not proof of model quality. Assignments should be based on evaluated model capabilities and the deployment's actual model metadata. This router does not claim that a model is trained, loaded, or reachable.

## Verification

`ai/test_function_router.py` covers explicit routing, ordered multi-model assignments, disabled-model exclusion, persistence, and invalid assignments. `ai/test_function_router_runtime.py` covers routing through live coordinator analysis and restored assignment state.

The router deliberately does not preassign Qwen3, DeepSeek, GPT-OSS, Gemma, or Codestral to functions. That mapping must come from the actual intended functional design and capability evidence, not assumptions based on model names.
