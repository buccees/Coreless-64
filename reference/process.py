"""Minimal Coreless process manager."""
from dataclasses import dataclass,field
@dataclass
class Process:
    pid:int
    name:str
    program:bytes=b""
    state:str="ready"
    pc:int=0
    registers:list=field(default_factory=lambda:[0]*32)
class ProcessManager:
    def __init__(self,machine):
        self.machine=machine; self.processes={}; self.next_pid=1; self.current=None
    def create(self,name,program=b""):
        p=Process(self.next_pid,name,bytes(program)); self.processes[p.pid]=p; self.next_pid+=1; return p
    def start(self,pid):
        p=self.processes[pid]; self.machine.load_program(p.program,0); self.machine.booted=True
        p.state="running"; self.current=pid
        self.machine.run()
        p.pc=self.machine.cpu.pc; p.registers=self.machine.cpu.r[:]
        p.state="exited" if self.machine.cpu.halted else "ready"; return p
    def kill(self,pid):
        p=self.processes[pid]; p.state="killed"; 
        if self.current==pid:self.current=None
    def list(self): return list(self.processes.values())
