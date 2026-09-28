"""Persistent Coreless machine-state storage."""
import base64,hashlib,json,os,tempfile
PAGE_SIZE=4096
class PersistentMachineImage:
    FORMAT=3
    def __init__(self,path=None):
        self.path=os.fspath(path) if path is not None else None
        self.objects={}; self.metadata={"format":self.FORMAT}
        if self.path and os.path.exists(self.path): self._load()
    def put(self,name,data):
        self.objects[name]=data.encode() if isinstance(data,str) else bytes(data); self._sync()
    def get(self,name): return self.objects[name]
    def checkpoint(self,name,state):
        blob=json.dumps(state,sort_keys=True,separators=(",",":")).encode()
        self.put(name,blob); return hashlib.sha256(blob).hexdigest()
    def ensure_ram(self,name,size):
        ram=self.metadata.setdefault("ram",{}); old=ram.get(name)
        if old is None: ram[name]={"size":size,"page_size":PAGE_SIZE}; self._sync()
        elif old["size"]!=size: raise ValueError("Coreless RAM size does not match machine image")
    def get_ram_page(self,name,page): return self.objects.get(f"ram/{name}/{page}",bytes(PAGE_SIZE))
    def put_ram_page(self,name,page,data):
        data=bytes(data)
        if len(data)!=PAGE_SIZE: raise ValueError("Coreless RAM pages must be 4096 bytes")
        self.objects[f"ram/{name}/{page}"]=data; self._sync()
    def manifest(self):
        return {"metadata":self.metadata.copy(),"objects":{k:len(v) for k,v in sorted(self.objects.items())}}
    def _load(self):
        with open(self.path,"r",encoding="utf-8") as f: image=json.load(f)
        if image.get("metadata",{}).get("format") not in (2,self.FORMAT): raise ValueError("unsupported Coreless image format")
        self.metadata=dict(image.get("metadata",{})); self.metadata["format"]=self.FORMAT
        self.objects={n:base64.b64decode(d.encode("ascii")) for n,d in image.get("objects",{}).items()}
    def _sync(self):
        if not self.path:return
        directory=os.path.dirname(os.path.abspath(self.path)); os.makedirs(directory,exist_ok=True)
        payload={"metadata":self.metadata,"objects":{n:base64.b64encode(d).decode("ascii") for n,d in sorted(self.objects.items())}}
        fd,tmp=tempfile.mkstemp(prefix=".coreless-",suffix=".tmp",dir=directory)
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as f:
                json.dump(payload,f,sort_keys=True,separators=(",",":")); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
