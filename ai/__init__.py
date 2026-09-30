"""Coreless AI integration layer."""

from .audit import AuditLog, AuditRecord
from .commands import CommandDispatcher, CommandResult, TerminalCommand
from .management import ManagementPlane, ManagementResult
from .policy import DeterministicPolicy, PolicyDecision
from .resource_control import CorelessResourceController
from .session import AISession, SessionEvent, TerminalMessage
from .telemetry import TelemetryProvider, TelemetrySnapshot

from .local_runtime import LocalModelSpec, LocalOpenAICompatibleCore, build_default_local_cores, register_default_local_cores
