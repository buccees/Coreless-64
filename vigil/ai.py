"""VIGIL bridge to the shared Coreless Qwen3 AI core.

VIGIL is a client of the existing registry. It never loads model weights,
creates a runtime, or broad-casts spatial requests to every enabled model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ai.interfaces import AIRequest
from ai.registry import AICoreRegistry
from .model import WorldEntity


@dataclass(frozen=True)
class AnalysisResult:
    text: str
    grounded_entity_ids: tuple[str, ...]
    model_id: str
    confidence: float | None = None


class CorelessVigilAI:
    """Send optional VIGIL analysis to one already-registered Coreless AI core."""

    def __init__(
        self,
        registry: AICoreRegistry | None = None,
        *,
        model_id: str = "qwen3",
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id must not be empty")
        self.registry = registry
        self.model_id = model_id

    def available(self) -> bool:
        if self.registry is None:
            return False
        try:
            return self.registry.descriptor(self.model_id).enabled
        except KeyError:
            return False

    def analyze(
        self,
        question: str,
        entities: Sequence[WorldEntity],
        *,
        request_id: str = "vigil-analysis",
    ) -> AnalysisResult | None:
        if not self.available():
            return None

        entity_ids = tuple(entity.entity_id for entity in entities)
        context = {
            "source": "vigil",
            "task_kind": "EXPLAIN_RESULT",
            "entities": [
                {
                    "id": entity.entity_id,
                    "type": entity.entity_type.value,
                    "label": entity.label,
                    "position": entity.position,
                    "confidence": entity.confidence,
                    "valid": entity.valid,
                    "fresh": entity.fresh,
                }
                for entity in entities
            ],
        }
        request = AIRequest(
            request_id=request_id,
            prompt=(
                "Analyze the supplied VIGIL world-state information. "
                "Do not invent environmental facts, change world state, "
                "authorize actions, or claim physical authority. "
                f"Question: {question}"
            ),
            context=context,
        )
        try:
            # Explicit model selection guarantees VIGIL does not fan out to
            # unrelated enabled models or create a private inference runtime.
            results = self.registry.infer(request, model_ids=(self.model_id,))
        except (KeyError, RuntimeError, TimeoutError):
            # Conversational interpretation is optional. Coreless input and
            # deterministic spatial processing must continue if AI is down.
            return None
        if not results:
            return None
        result = results[0]
        if result.request_id != request_id or result.model_id != self.model_id or not isinstance(result.text, str):
            return None
        return AnalysisResult(
            text=result.text,
            grounded_entity_ids=entity_ids,
            model_id=result.model_id,
            confidence=None,
        )


# Compatibility alias: callers can refer to the VIGIL bridge without implying
# that VIGIL owns a separate AI runtime.
OptionalAIAnalyzer = CorelessVigilAI
