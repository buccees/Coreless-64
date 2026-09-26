import sys;sys.path.insert(0,".")
from storage import PersistentMachineImage
def test_persistent_machine_image():
    p=PersistentMachineImage();p.put("kernel",b"coreless");d=p.checkpoint("checkpoint-0",{"pc":16,"cpu_count":4});assert len(d)==64;assert p.get("kernel")==b"coreless"
