"""Persistent Coreless machine-state reference model."""
import json,hashlib
class PersistentMachineImage:
    def __init__(self):self.objects={};self.metadata={"format":1}
    def put(self,name,data):self.objects[name]=data.encode() if isinstance(data,str) else bytes(data)
    def get(self,name):return self.objects[name]
    def checkpoint(self,name,state):
        blob=json.dumps(state,sort_keys=True,separators=(",",":")).encode();self.put(name,blob);return hashlib.sha256(blob).hexdigest()
    def manifest(self):return {"metadata":self.metadata.copy(),"objects":{k:len(v) for k,v in sorted(self.objects.items())}}
