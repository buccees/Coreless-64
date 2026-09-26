"""Minimal Coreless network service layer."""
class NetworkStack:
    def __init__(self,device):
        self.device=device; self.config={"ipv4":None,"ipv6":None,"hostname":"coreless"}
    def configure(self,**kwargs): self.config.update(kwargs)
    def ping_frame(self,target):
        return self.device.transmit(("PING "+str(target)).encode(),str(target))
    def receive(self):
        p=self.device.poll_rx()
        return p.data.decode(errors="replace") if p else None
