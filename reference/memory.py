"""Paged Coreless virtual RAM backed by persistent storage."""
PAGE_SIZE=4096
class VirtualRAM:
    def __init__(self,size,image=None,name="ram"):
        if size<=0 or size%PAGE_SIZE: raise ValueError("Coreless RAM size must be a positive page multiple")
        self.size=size; self.image=image; self.name=name; self.cache={}; self.dirty=set()
        if image is not None: image.ensure_ram(name,size)
    def __len__(self): return self.size
    def _check(self,a,b):
        if a<0 or b<a or b>self.size: raise IndexError("Coreless RAM access outside virtual RAM")
    def _page(self,n):
        if n not in self.cache: self.cache[n]=bytearray(self.image.get_ram_page(self.name,n) if self.image else bytes(PAGE_SIZE))
        return self.cache[n]
    def _read(self,a,b):
        self._check(a,b); out=bytearray()
        while a<b:
            n,o=divmod(a,PAGE_SIZE); c=min(b-a,PAGE_SIZE-o); out.extend(self._page(n)[o:o+c]); a+=c
        return bytes(out)
    def _write(self,a,data):
        data=bytes(data); self._check(a,a+len(data)); p=0
        while p<len(data):
            n,o=divmod(a+p,PAGE_SIZE); c=min(len(data)-p,PAGE_SIZE-o); self._page(n)[o:o+c]=data[p:p+c]; self.dirty.add(n); p+=c
    def flush(self):
        if self.image:
            for n in sorted(self.dirty): self.image.put_ram_page(self.name,n,self._page(n))
        self.dirty.clear()
    def __getitem__(self,k):
        if isinstance(k,slice):
            a,b,s=k.indices(self.size)
            if s!=1: return self._read(a,b)[::s]
            return self._read(a,b)
        if k<0:k+=self.size
        self._check(k,k+1); return self._page(k//PAGE_SIZE)[k%PAGE_SIZE]
    def __setitem__(self,k,v):
        if isinstance(k,slice):
            a,b,s=k.indices(self.size)
            if s!=1 or len(v)!=b-a: raise ValueError("Coreless RAM slice assignment must preserve length")
            self._write(a,v); return
        if k<0:k+=self.size
        self._write(k,bytes((v,)))
