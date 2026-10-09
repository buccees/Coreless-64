"""Persistent Coreless machine-state storage."""
import base64
import hashlib
import json
import os
import re
import tempfile

PAGE_SIZE = 4096


class PersistentMachineImage:
    FORMAT = 3

    def __init__(self, path=None):
        self.path = os.fspath(path) if path is not None else None
        self.objects = {}
        self.metadata = {"format": self.FORMAT}
        if self.path and os.path.exists(self.path):
            self._load()

    def put(self, name, data, sync=True):
        payload = data.encode() if isinstance(data, str) else bytes(data)
        structures = self.metadata.get("structural_allocations", {})
        allocation = structures.get(name)
        if allocation is not None and len(payload) != allocation["size"]:
            raise ValueError(
                "Coreless structural allocation size is fixed; "
                "use an explicit validated migration to change its shape"
            )
        self.objects[name] = payload
        if sync:
            self.sync()

    def reserve_structure(self, name, size, *, alignment=1, initial=None, sync=True):
        """Reserve a fixed-shape structural object for OS/CPU architecture state.

        This is a logical allocation contract, not a claim that the host device
        exposes physical SSD sectors or flash erase blocks.
        """
        if not isinstance(name, str) or not name or name.startswith("checkpoint/"):
            raise ValueError("structural allocation name must be a non-empty local key")
        if type(size) is not int or size <= 0:
            raise ValueError("structural allocation size must be a positive integer")
        if type(alignment) is not int or alignment <= 0 or alignment & (alignment - 1):
            raise ValueError("structural allocation alignment must be a positive power of two")
        payload = bytes(size) if initial is None else (
            initial.encode() if isinstance(initial, str) else bytes(initial)
        )
        if len(payload) != size:
            raise ValueError("initial structural data must match the reserved size")
        structures = self.metadata.setdefault("structural_allocations", {})
        allocation = structures.get(name)
        expected = {"size": size, "alignment": alignment}
        if allocation is not None and allocation != expected:
            raise ValueError("Coreless structural allocation shape cannot change")
        existing = self.objects.get(name)
        if existing is not None and len(existing) != size:
            raise ValueError("existing data does not match structural allocation size")
        structures[name] = expected
        if existing is None:
            self.objects[name] = payload
        if sync:
            self.sync()
        return name

    @staticmethod
    def _validate_structural_allocations(metadata, objects):
        structures = metadata.get("structural_allocations", {})
        if not isinstance(structures, dict):
            raise ValueError("invalid Coreless structural allocation manifest")
        for name, allocation in structures.items():
            if (
                not isinstance(name, str) or not name
                or not isinstance(allocation, dict)
                or type(allocation.get("size")) is not int
                or allocation["size"] <= 0
                or type(allocation.get("alignment")) is not int
                or allocation["alignment"] <= 0
                or allocation["alignment"] & (allocation["alignment"] - 1)
            ):
                raise ValueError("invalid Coreless structural allocation manifest")
            payload = objects.get(name)
            if payload is None or len(payload) != allocation["size"]:
                raise ValueError("Coreless structural allocation shape is inconsistent")

    def get(self, name):
        return self.objects[name]

    def checkpoint(self, name, state):
        blob = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
        self.put(name, blob)
        return hashlib.sha256(blob).hexdigest()

    def create_checkpoint(self, name):
        """Persist a complete machine-image snapshot, not only CPU metadata."""
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name)).strip("._") or "machine"
        snapshot = {
            "format": self.FORMAT,
            "metadata": self.metadata.copy(),
            "objects": {
                key: base64.b64encode(value).decode("ascii")
                for key, value in sorted(self.objects.items())
                if not key.startswith("checkpoint/")
            },
        }
        blob = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        self.put("checkpoint/" + safe, blob, sync=False)
        self.put("machine", blob, sync=False)
        self.sync()
        return hashlib.sha256(blob).hexdigest()

    def restore_checkpoint(self, name):
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name)).strip("._") or "machine"
        raw = self.objects.get("checkpoint/" + safe)
        if raw is None:
            raise KeyError("Coreless checkpoint not found: " + safe)
        snapshot = json.loads(raw.decode("utf-8"))
        if snapshot.get("format") != self.FORMAT:
            raise ValueError("unsupported Coreless checkpoint format")
        snapshot_metadata = dict(snapshot.get("metadata", {}))
        snapshot_objects = {
            key: base64.b64decode(value.encode("ascii"))
            for key, value in snapshot.get("objects", {}).items()
        }
        current_structures = self.metadata.get("structural_allocations", {})
        snapshot_structures = snapshot_metadata.get("structural_allocations", {})
        if current_structures != snapshot_structures:
            raise ValueError("checkpoint cannot change Coreless structural allocation shape")
        self._validate_structural_allocations(snapshot_metadata, snapshot_objects)
        self.metadata = snapshot_metadata
        self.metadata["format"] = self.FORMAT
        checkpoints = {
            key: value for key, value in self.objects.items()
            if key.startswith("checkpoint/")
        }
        self.objects = snapshot_objects
        self.objects.update(checkpoints)
        self.sync()
        return hashlib.sha256(raw).hexdigest()

    def list_checkpoints(self):
        return sorted(
            key[len("checkpoint/"):]
            for key in self.objects
            if key.startswith("checkpoint/")
        )

    def save_machine_state(self, state):
        return self.checkpoint("machine/state", state)

    def load_machine_state(self):
        raw = self.objects.get("machine/state")
        if raw is None:
            return None
        return json.loads(raw.decode())

    def ensure_ram(self, name, size):
        ram = self.metadata.setdefault("ram", {})
        old = ram.get(name)
        if old is None:
            ram[name] = {"size": size, "page_size": PAGE_SIZE}
            self.sync()
        elif old["size"] != size:
            raise ValueError("Coreless RAM size does not match machine image")

    def get_ram_page(self, name, page):
        return self.objects.get(f"ram/{name}/{page}", bytes(PAGE_SIZE))

    def put_ram_page(self, name, page, data, sync=True):
        data = bytes(data)
        if len(data) != PAGE_SIZE:
            raise ValueError("Coreless RAM pages must be 4096 bytes")
        self.objects[f"ram/{name}/{page}"] = data
        if sync:
            self.sync()

    def manifest(self):
        return {
            "metadata": self.metadata.copy(),
            "objects": {k: len(v) for k, v in sorted(self.objects.items())},
        }

    def _load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            image = json.load(f)
        if image.get("metadata", {}).get("format") not in (2, self.FORMAT):
            raise ValueError("unsupported Coreless image format")
        self.metadata = dict(image.get("metadata", {}))
        self.metadata["format"] = self.FORMAT
        self.objects = {
            name: base64.b64decode(data.encode("ascii"))
            for name, data in image.get("objects", {}).items()
        }
        self._validate_structural_allocations(self.metadata, self.objects)

    def sync(self):
        if not self.path:
            return
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        payload = {
            "metadata": self.metadata,
            "objects": {
                name: base64.b64encode(data).decode("ascii")
                for name, data in sorted(self.objects.items())
            },
        }
        fd, tmp = tempfile.mkstemp(prefix=".coreless-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, sort_keys=True, separators=(",", ":"))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
