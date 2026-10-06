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
    response_for,
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


def test_response_for_preserves_correlation_across_wire_round_trip():
    request = DeviceCommand(OP_EXECUTE, 77, b"run")
    reply = response_for(request, b"accepted")
    assert is_response(reply)
    assert not is_error(reply)
    assert reply.request_id == 77
    assert reply.opcode == OP_EXECUTE
    assert reply.payload == b"accepted"


def test_command_rejects_bad_magic():
    encoded = bytearray(DeviceCommand(OP_EXECUTE, 1).encode())
    encoded[:8] = b"BADMAGIC"
    with pytest.raises(ValueError, match="magic"):
        DeviceCommand.decode(bytes(encoded))


def test_command_rejects_bad_payload_length():
    encoded = DeviceCommand(OP_EXECUTE, 1, b"payload").encode()
    with pytest.raises(ValueError, match="payload length"):
        DeviceCommand.decode(encoded[:-1])


def test_command_rejects_unsupported_flags_on_encode():
    with pytest.raises(ValueError, match="unsupported Coreless command flags"):
        DeviceCommand(OP_EXECUTE, 1, flags=0x4).encode()


def test_command_rejects_error_flag_without_response():
    with pytest.raises(ValueError, match="error flag requires response"):
        DeviceCommand(OP_EXECUTE, 1, flags=FLAG_ERROR).encode()


def test_command_rejects_unsupported_flags_on_decode():
    encoded = bytearray(DeviceCommand(OP_EXECUTE, 1).encode())
    encoded[-8:] = (0x4).to_bytes(8, "little")
    with pytest.raises(ValueError, match="unsupported Coreless command flags"):
        DeviceCommand.decode(bytes(encoded))


def test_command_rejects_error_flag_without_response_on_decode():
    encoded = bytearray(DeviceCommand(OP_EXECUTE, 1).encode())
    encoded[-8:] = FLAG_ERROR.to_bytes(8, "little")
    with pytest.raises(ValueError, match="error flag requires response"):
        DeviceCommand.decode(bytes(encoded))


def test_command_round_trip_helper_preserves_wire_command():
    command = DeviceCommand(OP_EXECUTE, 123, b"payload", flags=0)
    assert round_trip(command) == command

    
def test_storage_write_payload_round_trip():
    from device_command import decode_storage_write, encode_storage_write
    payload = encode_storage_write("config/name", b"coreless")
    assert decode_storage_write(payload) == ("config/name", b"coreless")


def test_storage_write_payload_rejects_empty_or_truncated_key():
    from device_command import decode_storage_write, encode_storage_write
    with pytest.raises(ValueError, match="must not be empty"):
        encode_storage_write("")
    with pytest.raises(ValueError, match="missing key length"):
        decode_storage_write(b"")
    with pytest.raises(ValueError, match="truncated"):
        decode_storage_write(b"\x04\x00ab")
