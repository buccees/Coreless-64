import sys;sys.path.insert(0,".")
from io import NetworkDevice,GraphicsDevice
def test_network_device():
    n=NetworkDevice(); n.configure(True,("checksum","dma")); n.transmit(b"abc","host"); p=n.receive(b"xyz","peer")
    assert n.tx[0].data==b"abc" and n.poll_rx()==p
def test_graphics_surface_and_present():
    g=GraphicsDevice(); s=g.create_surface(4,4); g.submit(("clear",0)); s.ready=True; g.present(s); g.input(("key","A"))
    assert g.scanout is s and g.poll_input()==("key","A")
