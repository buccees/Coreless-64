"""Coreless-64 conformance tests for architectural invariants."""

from encoding import (
    decode, encode_r, encode_i, instruction_length, instruction_length_class,
    IllegalEncoding, OP_EXT64, OP_EXT128, OP_ESCAPE,
)

def expect_illegal(fn):
    try:
        fn()
    except IllegalEncoding:
        return
    raise AssertionError("expected IllegalEncoding")

def test_all_base_length_classes_are_four_bytes():
    for op in range(0x00, 0x1D):
        assert instruction_length(op << 27) == 4

def test_length_prefixes():
    assert instruction_length(OP_EXT64 << 27) == 8
    assert instruction_length(OP_EXT128 << 27) == 16
    expect_illegal(lambda: instruction_length(OP_ESCAPE << 27))

def test_extended_prefix_requires_length_aware_decode():
    expect_illegal(lambda: decode(OP_EXT64 << 27))
    expect_illegal(lambda: decode(OP_EXT128 << 27))

def test_scalar_r_round_trip():
    for f,name in [(0,"ADD"),(1,"SUB"),(2,"MUL"),(7,"AND"),(9,"XOR"),(11,"SHL"),(16,"SLT"),(20,"NEG")]:
        w=encode_r(f,31,30,29)
        assert decode(w)==(name,31,30,29)

def test_scalar_i_signed_boundaries():
    for imm in (-2048,-1,0,1,2047):
        w=encode_i(0,1,2,imm)
        assert decode(w)==("ADDI",1,2,imm)

def test_scalar_i_rejects_out_of_range():
    expect_illegal(lambda: encode_i(0,1,2,2048))
    expect_illegal(lambda: encode_i(0,1,2,-2049))

def test_reserved_r_bits_are_illegal():
    expect_illegal(lambda: decode(encode_r(0,1,2,3) | (1 << 5)))

def test_branch_fields_and_signed_offset():
    w=(4<<27)|(7<<22)|(8<<17)|(0<<12)|((-4)&0xfff)
    assert decode(w)==("BEQ",7,8,-4)

def test_ret_has_no_operands():
    w=(5<<27)|(4<<12)
    assert decode(w)==("RET",0,0,0)

def test_ret_rejects_nonzero_fields():
    expect_illegal(lambda: decode((5<<27)|(1<<22)|(4<<12)))
    expect_illegal(lambda: decode((5<<27)|(4<<12)|1))


def test_extended_header_fields():
    w=(OP_EXT128<<27)|(0x3<<23)|(0x26<<17)|(31<<12)|(30<<7)|(29<<2)|2
    from encoding import decode_extended_header
    assert decode_extended_header(w)==(3,0x26,31,30,29,2)

def test_stream_walks_mixed_lengths():
    from encoding import to_bytes, decode_stream
    base=encode_i(0,1,2,7)
    ext=(OP_EXT64<<27)|(0x0<<23)|(0x01<<17)
    payload=0x12345678
    result=decode_stream(to_bytes(base)+to_bytes(ext)+to_bytes(payload))
    assert [x[1] for x in result]==[4,8]
    assert result[0][2]==("ADDI",1,2,7)

def test_stream_rejects_truncation():
    from encoding import to_bytes, decode_stream
    ext=(OP_EXT128<<27)
    expect_illegal(lambda: decode_stream(to_bytes(ext)+to_bytes(0)+to_bytes(0)))

def test_stream_does_not_decode_payload_as_instruction():
    from encoding import to_bytes, decode_stream
    ext=(OP_EXT64<<27)
    payload=encode_r(0,9,8,7)
    result=decode_stream(to_bytes(ext)+to_bytes(payload))
    assert len(result)==1
    assert result[0][1]==8
