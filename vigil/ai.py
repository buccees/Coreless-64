"""Optional AI analysis boundary for VIGIL.

AI consumes structured VIGIL information. It does not become the authority for
world state, authorization, or physical action.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Sequence
from .model import WorldEntity


@dataclass(frozen=True)
class AnalysisResult:
    text: str
    grounded_entity_ids: tuple[str, ...]
    confidence: float | None = None


class WorldAnalysisProvider(Protocol):
    def analyze(self, question: str, entities: Sequence[WorldEntity]) -> AnalysisResult:
        ...


class OptionalAIAnalyzer:
    def __init__(self, provider: WorldAnalysisProvider | None = None) -> None:
        self.provider = provider

    def available(self) -> bool:
        return self.provider is not None

    def analyze(self, question: str, entities: Sequence[WorldEntity]) -> AnalysisResult | None:
        if self.provider is None:
            return None
        return self.provider.analyze(question, entities)
