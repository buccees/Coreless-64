"""Preflight checks for the Coreless-64 ISA contract.

These tests deliberately derive expectations from the architectural tables and
from explicitly documented API boundaries. They are intended to catch test
assumptions before larger conformance batches are added.
"""
import sys
sys.path.insert(0, ".")

import pytest

from encoding import (
    ALUR, ALUI, BRANCH, JUMP, SYSTEM, LOAD,
    OP_EXT64, OP_EXT128, OP_ESCAPE,
    IllegalEncoding, decode, decode_extended_header,
    decode_stream, encode_r, encode_i, encode_syscall,
    instruction_length,
)


def test_defined_opcode_tables_are_unique_and_nonempty():
    for table in (ALUR, ALUI, BRANCH, JUMP, SYSTEM, LOAD):
        assert table
        assert len(table) == len(set(table))
        assert len(table) == len(set(table.values()))


def test_base_alu_table_is_the_round_trip_source_of_truth():
    for funct, name in ALUR.items():
        assert decode(encode_r(funct, 31, 30, 29)) == (name, 31, 30, 29)


def test_immediate_table_is_the_round_trip_source_of_truth():
    for funct, name in ALUI.items():
        assert decode(encode_i(funct, 31, 30, -1)) == (name, 31, 30, -1)


def test_syscall_boundary_contract_is_an_encoder_api_error():
    assert decode(encode_syscall(0))[0] == "SYSCALL"
    assert decode(encode_syscall(2047))[0] == "SYSCALL"
    with pytest.raises(ValueError):
        encode_syscall(-1)
    with pytest.raises(ValueError):
        encode_syscall(2048)


def test_instruction_length_contract_is_independent_of_semantic_decode():
    assert instruction_length(0 << 27) == 4
    assert instruction_length(OP_EXT64 << 27) == 8
    assert instruction_length(OP_EXT128 << 27) == 16
    with pytest.raises(IllegalEncoding):
        instruction_length(OP_ESCAPE << 27)


def test_extended_header_reserved_classes_are_rejected_by_header_decoder():
    for cls in (9, 10, 15):
        word = (OP_EXT128 << 27) | (cls << 23) | 2
        with pytest.raises(IllegalEncoding):
            decode_extended_header(word)


def test_stream_decoder_owns_instruction_framing():
    word = (OP_EXT128 << 27) | (3 << 23) | 2
    payload = b"".join(i.to_bytes(4, "little") for i in range(3))
    decoded = decode_stream(word.to_bytes(4, "little") + payload)
    assert decoded[0][0] == 0
    assert decoded[0][1] == 16


def test_stream_decoder_rejects_truncated_extended_instruction():
    word = (OP_EXT128 << 27) | (3 << 23) | 2
    with pytest.raises(IllegalEncoding):
        decode_stream(word.to_bytes(4, "little") + b"\x00\x00\x00\x00")


def test_reserved_primary_opcodes_are_not_valid_base_instructions():
    for opcode in (13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28):
        with pytest.raises(IllegalEncoding):
            decode(opcode << 27)
