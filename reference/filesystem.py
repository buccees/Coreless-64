"""Small persistent filesystem for the Coreless reference machine."""
import json
class FileSystem:
    def __init__(self,image=None):
        self.image=image; self.files={}
        if image:
            raw=image.objects.get("filesystem")
            if raw:
                self.files=json.loads(raw.decode())
    def reload(self):
        self.files = {}
        if self.image:
            raw = self.image.objects.get("filesystem")
            if raw:
                self.files = json.loads(raw.decode())

    def write(self,path,data):
        path=self._path(path); self.files[path]=bytes(data).hex(); self._sync()
    def read(self,path):
        path=self._path(path)
        if path not in self.files: raise FileNotFoundError(path)
        return bytes.fromhex(self.files[path])
    def exists(self,path): return self._path(path) in self.files
    def list(self,prefix="/"):
        prefix=self._path(prefix).rstrip("/")+"/" if prefix!="/" else "/"
        return sorted(k for k in self.files if k.startswith(prefix))
    def delete(self,path):
        path=self._path(path)
        if path not in self.files: raise FileNotFoundError(path)
        del self.files[path]; self._sync()
    def _path(self,p):
        p="/"+str(p).lstrip("/"); parts=[x for x in p.split("/") if x not in ("",".")]
        out=[]
        for x in parts:
            if x=="..":
                if out: out.pop()
            else: out.append(x)
        return "/"+"/".join(out)
    def _sync(self):
        if self.image:
            self.image.put("filesystem",json.dumps(self.files,sort_keys=True))
