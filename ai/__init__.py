"""Coreless AI integration layer.

Optional adapters live here. The Coreless CPU and architectural control
boundaries do not depend on a remote AI service.
"""

from .policy import DeterministicPolicy, PolicyDecision

from .session import AISession, SessionEvent, TerminalMessage

from .resource_control import CorelessResourceController
