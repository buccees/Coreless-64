import sys;sys.path.insert(0,".")
from machine_runtime import CorelessMachine
from encoding import encode_base_r,encode_base_i

def test_machine_boot_and_run():
    m=CorelessMachine(4096); program=b"".join([
        encode_base_i("ADDI",1,0,42).to_bytes(4,"little"),
        encode_base_r("ADD",2,1,1).to_bytes(4,"little"),
        encode_base_i("ADDI",3,2,1).to_bytes(4,"little"),
        (0x30000001).to_bytes(4,"little"), # HALT
    ])
    m.boot(program); steps=m.run()
    assert steps==4 and m.cpu.read_reg(1)==42 and m.cpu.read_reg(2)==84 and m.cpu.read_reg(3)==85

def test_machine_checkpoint():
    m=CorelessMachine(4096,2); m.boot(bytes.fromhex("00000020"))
    digest=m.checkpoint(); assert len(digest)==64 and m.storage.get("machine")
