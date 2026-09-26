"""Coreless-64 program loader and executable validation."""
from encoding import decode_stream

class ProgramLoader:
    MAGIC = b"COREX64\x00"
    VERSION = 1
    HEADER_SIZE = 16

    def __init__(self, machine):
        self.machine = machine

    def validate(self, program):
        return decode_stream(bytes(program))

    def load(self, program, address=0):
        program = bytes(program)
        self.validate(program)
        self.machine.load_program(program, address)
        return {"entry": address, "size": len(program)}

    def load_executable(self, image, address=0):
        image = bytes(image)
        if len(image) < self.HEADER_SIZE or image[:8] != self.MAGIC:
            raise ValueError("invalid COREX64 executable")
        version = int.from_bytes(image[8:10], "little")
        entry = int.from_bytes(image[10:14], "little")
        size = int.from_bytes(image[14:16], "little")
        if version != self.VERSION or size != len(image) - self.HEADER_SIZE:
            raise ValueError("unsupported or malformed COREX64 executable")
        code = image[self.HEADER_SIZE:]
        self.validate(code)
        load_address = address
        self.machine.load_program(code, load_address)
        return {"entry": load_address + entry, "size": len(code), "version": version}

    @classmethod
    def make_executable(cls, program, entry=0):
        program = bytes(program)
        cls_dummy = cls.__new__(cls)
        cls_dummy.validate = lambda p: decode_stream(bytes(p))
        cls_dummy.validate(program)
        header = cls.MAGIC
        header += cls.VERSION.to_bytes(2, "little")
        header += int(entry).to_bytes(4, "little")
        header += len(program).to_bytes(2, "little")
        return header + program
