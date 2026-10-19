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

    def __init__(self, path=None, *, policy=None):
        self.path = os.fspath(path) if path is not None else None
        self.policy = policy
        self.objects = {}
        self.metadata = {"format": self.FORMAT}
        if self.path:
            self._recover_transaction()
            if os.path.exists(self.path):
                self._load()

    def _validate_write(self, name):
        if self.policy is not None:
            self.policy.validate_write(name)

    def put(self, name, data, sync=True):
        self._validate_write(name)
        self.objects[name] = data.encode() if isinstance(data, str) else bytes(data)
        if sync:
            self.sync()

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
        restored_objects = {
            key: base64.b64decode(value.encode("ascii"))
            for key, value in snapshot.get("objects", {}).items()
        }
        checkpoints = {
            key: value for key, value in self.objects.items()
            if key.startswith("checkpoint/")
        }
        restored_objects.update(checkpoints)
        # Validate every changed, added, or removed object before mutating the
        # live image. This keeps a policy rejection from partially restoring.
        if self.policy is not None:
            for key in self.objects.keys() | restored_objects.keys():
                if self.objects.get(key) != restored_objects.get(key):
                    self._validate_write(key)
        restored_metadata = dict(snapshot.get("metadata", {}))
        restored_metadata["format"] = self.FORMAT
        self.metadata = restored_metadata
        self.objects = restored_objects
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
        self.put(f"ram/{name}/{page}", data, sync=sync)

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

    def _fsync_directory(self, directory):
        dir_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

    def _write_durable_file(self, path, data, directory):
        fd, tmp = tempfile.mkstemp(prefix=".coreless-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            self._fsync_directory(directory)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _recover_transaction(self):
        """Recover the last committed image if a sync was interrupted.

        The journal remains present until the new image's rename is durable
        and the commit is finalized. If startup finds the journal, it restores
        the previous image rather than guessing that an interrupted write
        committed successfully.
        """
        if not self.path:
            return
        directory = os.path.dirname(os.path.abspath(self.path))
        journal = self.path + ".txn"
        previous = self.path + ".prev"
        if not os.path.exists(journal):
            return
        try:
            with open(journal, "r", encoding="utf-8") as f:
                transaction = json.load(f)
            had_previous = transaction.get("had_previous") is True
            if had_previous:
                if not os.path.exists(previous):
                    raise RuntimeError("machine image recovery journal has no previous image")
                with open(previous, "rb") as f:
                    old_payload = f.read()
                # Keep .prev until the journal removal itself is durable, so
                # recovery can safely retry after another interruption.
                self._write_durable_file(self.path, old_payload, directory)
            elif os.path.exists(self.path):
                os.unlink(self.path)
                self._fsync_directory(directory)
            os.unlink(journal)
            self._fsync_directory(directory)
            if os.path.exists(previous):
                os.unlink(previous)
                self._fsync_directory(directory)
        except Exception as exc:
            raise RuntimeError("machine image transaction recovery could not be made durable") from exc

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
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        previous = self.path + ".prev"
        journal = self.path + ".txn"
        had_previous = os.path.exists(self.path)
        tmp = None
        try:
            # Preserve the last committed image before making the transaction
            # visible. The journal makes an interrupted replacement recover
            # to this image on the next open.
            if had_previous:
                with open(self.path, "rb") as old_file:
                    self._write_durable_file(previous, old_file.read(), directory)
            marker = json.dumps({"had_previous": had_previous}, sort_keys=True).encode("utf-8")
            self._write_durable_file(journal, marker, directory)

            fd, tmp = tempfile.mkstemp(prefix=".coreless-", suffix=".tmp", dir=directory)
            with os.fdopen(fd, "wb") as f:
                f.write(encoded)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
            tmp = None
            self._fsync_directory(directory)

            # Removing the journal is the commit point. If a crash occurs
            # earlier, startup rolls back using .prev.
            os.unlink(journal)
            self._fsync_directory(directory)
            if os.path.exists(previous):
                os.unlink(previous)
                self._fsync_directory(directory)
        except Exception as sync_error:
            if tmp is not None and os.path.exists(tmp):
                os.unlink(tmp)
            if os.path.exists(journal):
                try:
                    self._recover_transaction()
                except Exception as recovery_error:
                    raise RuntimeError(
                        "machine image sync failed and rollback durability is uncertain"
                    ) from recovery_error
            raise sync_error


class StorageRegionPolicy:
    """Explicit namespace policy for Coreless-managed storage objects.

    This policy classifies logical object names only. It does not reserve
    physical blocks or enforce quotas in the host filesystem.
    """

    def __init__(self):
        self._regions = {}

    def register_region(self, name, prefixes, *, mutable, object_names=()):
        if not isinstance(name, str) or not name or name in self._regions:
            raise ValueError("storage region name must be unique and non-empty")
        normalized = tuple(prefixes)
        if not normalized or any(
            not isinstance(prefix, str) or not prefix or not prefix.endswith("/")
            for prefix in normalized
        ):
            raise ValueError("storage region prefixes must be non-empty directory prefixes")
        exact_names = tuple(object_names)
        if any(
            not isinstance(object_name, str) or not object_name or "/" in object_name
            for object_name in exact_names
        ):
            raise ValueError("storage object names must be non-empty root-level names")
        if len(set(exact_names)) != len(exact_names):
            raise ValueError("storage object names must be unique")
        for existing_name, (existing_prefixes, existing_names, _) in self._regions.items():
            prefixes_overlap = any(
                prefix.startswith(old) or old.startswith(prefix)
                for prefix in normalized
                for old in existing_prefixes
            )
            names_overlap = bool(set(exact_names) & set(existing_names))
            names_hit_prefix = any(
                object_name.startswith(prefix)
                for object_name in exact_names
                for prefix in existing_prefixes
            ) or any(
                object_name.startswith(prefix)
                for object_name in existing_names
                for prefix in normalized
            )
            if prefixes_overlap or names_overlap or names_hit_prefix:
                raise ValueError(
                    f"storage region names or prefixes overlap with region {existing_name!r}"
                )
        self._regions[name] = (normalized, exact_names, bool(mutable))

    def region_for(self, object_name):
        if not isinstance(object_name, str) or not object_name:
            raise ValueError("storage object name must be non-empty")
        matches = [
            name for name, (prefixes, exact_names, _) in self._regions.items()
            if object_name in exact_names
            or any(object_name.startswith(prefix) for prefix in prefixes)
        ]
        if not matches:
            raise ValueError(f"no registered storage region for object {object_name!r}")
        if len(matches) != 1:
            raise ValueError(f"ambiguous storage region for object {object_name!r}")
        return matches[0]

    def validate_write(self, object_name):
        region = self.region_for(object_name)
        if not self._regions[region][2]:
            raise PermissionError(f"storage region {region!r} is immutable")
        return region
