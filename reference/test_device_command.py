import sys
sys.path.insert(0, ".")

import pytest

from device_command import (
    FLAG_ERROR,
    FLAG_RESPONSE,
    HEADER_SIZE,
    MAGIC,
    OP_CAPABILITIES,
    OP_EXECUTE,
    DeviceCommand,
    is_error,
    is_response,
    response,
    round_trip,
)


def test_command_round_trips():
    command = DeviceCommand(OP_EXECUTE, 42, b"run")
    encoded = command.encode()
    decoded = DeviceCommand.decode(encoded)
    assert encoded.startswith(MAGIC)
    assert len(encoded) == HEADER_SIZE + 3
    assert decoded == command


def test_response_preserves_request_identity():
    request = DeviceCommand(OP_CAPABILITIES, 99, b"")
    reply = response(request, b"caps")
    assert reply.request_id == request.request_id
    assert reply.opcode == request.opcode
    assert is_response(reply)
    assert not is_error(reply)
    assert reply.payload == b"caps"


def test_error_response_sets_error_flag():
    request = DeviceCommand(OP_EXECUTE, 7)
    reply = response(request, b"failed", error=True)
    assert reply.flags == FLAG_RESPONSE | FLAG_ERROR
    assert is_response(reply)
    assert is_error(reply)


def test_command_rejects_bad_magic():
    encoded = bytearray(DeviceCommand(OP_EXECUTE, 1).encode())
    encoded[:8] = b"BADMAGIC"
    with pytest.raises(ValueError, match="magic"):
        DeviceCommand.decode(bytes(encoded))


def test_command_rejects_bad_payload_length():
    encoded = DeviceCommand(OP_EXECUTE, 1, b"payload").encode()
    with pytest.raises(ValueError, match="payload length"):
        DeviceCommand.decode(encoded[:-1])


def test_command_round_trip_helper_preserves_wire_command():
    command = DeviceCommand(OP_EXECUTE, 123, b"payload", flags=0)
    assert round_trip(command) == command
