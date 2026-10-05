"""VIGIL AI bridge to the existing Coreless AI controller.

VIGIL does not create or host a second AI system. It submits grounded analysis
requests to the same registered Coreless AI cores used by the machine.
"""
from __future__ import annotations
import json
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
    """Use the existing Coreless AI registry/controller for VIGIL analysis."""

    def __init__(self, registry: AICoreRegistry | None = None) -> None:
        self.registry = registry

    def available(self) -> bool:
        return self.registry is not None and bool(self.registry.enabled_cores())

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
        results = self.registry.infer(request)
        if not results:
            return None
        result = results[0]
        return AnalysisResult(
            text=result.text,
            grounded_entity_ids=entity_ids,
            model_id=result.model_id,
            confidence=None,
        )


# Compatibility alias: callers can refer to the VIGIL bridge without implying
# that VIGIL owns a separate AI runtime.
OptionalAIAnalyzer = CorelessVigilAI
