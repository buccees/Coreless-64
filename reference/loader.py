"""Coreless-64 program loader."""
from encoding import decode_stream,IllegalEncoding
class ProgramLoader:
    def __init__(self,machine): self.machine=machine
    def validate(self,program):
        return decode_stream(bytes(program))
    def load(self,program,address=0):
        program=bytes(program); self.validate(program)
        self.machine.load_program(program,address)
        return {"address":address,"size":len(program)}
