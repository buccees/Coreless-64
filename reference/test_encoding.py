from encoding import (
    decode, encode_r, encode_i, to_bytes, from_bytes,
    instruction_length, instruction_length_class, IllegalEncoding,
    OP_EXT64, OP_EXT128, OP_ESCAPE,
)

def test_add_round_trip():
    w=encode_r(0,3,1,2)
    assert decode(w)==('ADD',3,1,2)
    assert from_bytes(to_bytes(w))==w

def test_addi_round_trip():
    w=encode_i(0,5,4,-17)
    assert decode(w)==('ADDI',5,4,-17)

def test_illegal_r_reserved():
    try:
        decode((1<<5))
    except IllegalEncoding:
        return
    assert False

def test_base_length():
    w=encode_r(0,3,1,2)
    assert instruction_length_class(w)==0
    assert instruction_length(w)==4

def test_extended_64_length():
    w=(OP_EXT64<<27)
    assert instruction_length_class(w)==OP_EXT64
    assert instruction_length(w)==8

def test_extended_128_length():
    w=(OP_EXT128<<27)
    assert instruction_length_class(w)==OP_EXT128
    assert instruction_length(w)==16

def test_future_escape_is_not_decodable():
    try:
        instruction_length(OP_ESCAPE<<27)
    except IllegalEncoding:
        return
    assert False

def test_extended_prefix_not_base_decoded():
    try:
        decode(OP_EXT64<<27)
    except IllegalEncoding:
        return
    assert False

def test_branch_register_fields():
    w=(4<<27)|(3<<22)|(7<<17)|(0<<12)
    assert decode(w)==('BEQ',3,7,0)
