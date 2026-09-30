from ai.commands import CommandDispatcher, TerminalCommand


def test_terminal_command_abi_accepts_structured_commands():
    result = CommandDispatcher().dispatch(
        TerminalCommand("c1", "inspect", {"target": "telemetry"})
    )
    assert result.status == "accepted"


def test_terminal_command_abi_requires_confirmation_for_sensitive_commands():
    result = CommandDispatcher().dispatch(
        TerminalCommand("c2", "approve", {"proposal_id": "p1"})
    )
    assert result.status == "confirmation_required"


def test_terminal_command_abi_rejects_unknown_commands():
    try:
        CommandDispatcher().dispatch(TerminalCommand("c3", "execute", {}))
    except ValueError:
        pass
    else:
        raise AssertionError("unknown command must be rejected")
