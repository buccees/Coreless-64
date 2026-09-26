"""Example first Coreless application image."""
from encoding import encode_i,encode_r
def hello_program():
    return b"".join([
        encode_i("ADDI",1,0,42).to_bytes(4,"little"),
        encode_r("ADD",2,1,1).to_bytes(4,"little"),
        bytes.fromhex("00000020"),
    ])
