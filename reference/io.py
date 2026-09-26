"""Coreless network and graphics reference devices."""
from dataclasses import dataclass, field

@dataclass
class Packet:
    data: bytes
    source: str = ""
    destination: str = ""

class NetworkDevice:
    def __init__(self, name="net0"):
        self.name=name; self.rx=[]; self.tx=[]; self.link_up=False
        self.features=set()
    def configure(self, link_up=True, features=()):
        self.link_up=link_up; self.features=set(features)
    def transmit(self,data,destination=""):
        if not self.link_up: raise RuntimeError("network link down")
        p=Packet(bytes(data),destination=destination); self.tx.append(p); return p
    def receive(self,data,source=""):
        p=Packet(bytes(data),source=source); self.rx.append(p); return p
    def poll_rx(self):
        return self.rx.pop(0) if self.rx else None

@dataclass
class DisplaySurface:
    width:int
    height:int
    pixel_format:str="XRGB8888"
    pixels:bytearray=field(default_factory=bytearray)
    ready:bool=False
    def __post_init__(self):
        if self.width<=0 or self.height<=0: raise ValueError("invalid surface")
        bpp={"XRGB8888":4,"ARGB8888":4,"RGB565":2}.get(self.pixel_format)
        if bpp is None: raise ValueError("unsupported pixel format")
        if not self.pixels: self.pixels=bytearray(self.width*self.height*bpp)

class GraphicsDevice:
    def __init__(self):
        self.surfaces=[]; self.scanout=None; self.input_events=[]; self.commands=[]
    def create_surface(self,width,height,pixel_format="XRGB8888"):
        s=DisplaySurface(width,height,pixel_format); self.surfaces.append(s); return s
    def submit(self,command):
        self.commands.append(command); return len(self.commands)-1
    def present(self,surface):
        if surface not in self.surfaces or not surface.ready: raise RuntimeError("surface not ready")
        self.scanout=surface
    def input(self,event):
        self.input_events.append(event)
    def poll_input(self):
        return self.input_events.pop(0) if self.input_events else None
