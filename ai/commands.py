"""Structured terminal command ABI for the human-AI control plane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class TerminalCommand:
    command_id: str
    kind: str
    arguments: Mapping[str, object]
    confirmation_required: bool = True


@dataclass(frozen=True)
class CommandResult:
    command_id: str
    status: str
    data: Mapping[str, object]


class CommandDispatcher:
    """Validate and classify commands; execution remains outside this ABI."""

    ALLOWED_KINDS = frozenset({"ask", "propose", "approve", "cancel", "inspect", "configure"})

    def dispatch(self, command: TerminalCommand) -> CommandResult:
        if command.kind not in self.ALLOWED_KINDS:
            raise ValueError("unsupported terminal command kind")
        if command.confirmation_required and command.kind in {"approve", "configure"}:
            return CommandResult(command.command_id, "confirmation_required", {})
        return CommandResult(command.command_id, "accepted", dict(command.arguments))
