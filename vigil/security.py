"""Security/authorization boundary for Coreless-native VIGIL."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationContext:
    session_id: str
    scopes: frozenset[str]
    # Stable campaign identity, distinct from the short-lived login session.
    crew_id: str | None = None


class AuthorizationService:
    def authorize(self, context: AuthorizationContext, required_scope: str) -> bool:
        return required_scope in context.scopes
