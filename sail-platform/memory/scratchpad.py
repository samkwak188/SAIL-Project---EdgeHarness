"""Shared scratchpad — file-locked, atomic writes, role-scoped access.

Concurrency rule (per plan §2.1): all writes go through this module with an
OS file lock + atomic write-rename. Parallel workers write only to their own
namespaced key (scratchpad:task/<step-id>/). The orchestrator merges after
worktree join.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from filelock import FileLock


class Scratchpad:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.path) + ".lock")
        if not self.path.exists():
            self._write_raw({})

    def read(self, key: str, role: str = "") -> Any:
        from memory.isolation import enforce_access

        with self.lock:
            data = self._read_raw()
        if not enforce_access(role, key):
            return None
        return data.get(key)

    def write(self, key: str, value: Any, role: str = "") -> bool:
        from memory.isolation import enforce_access

        if not enforce_access(role, key, write=True):
            return False
        with self.lock:
            data = self._read_raw()
            data[key] = value
            self._write_raw(data)
        return True

    def slice(self, keys: list[str], role: str = "") -> dict[str, Any]:
        """Return a filtered slice containing only the listed keys (access-checked)."""
        from memory.isolation import enforce_access

        with self.lock:
            data = self._read_raw()
        out = {}
        for k in keys:
            if enforce_access(role, k) and k in data:
                out[k] = data[k]
        return out

    def merge(self, namespace: str, partial: dict[str, Any]) -> None:
        """Merge a parallel worker's namespaced partial into the shared state."""
        with self.lock:
            data = self._read_raw()
            bucket = data.setdefault(namespace, {})
            if isinstance(bucket, dict):
                bucket.update(partial)
            self._write_raw(data)

    def _read_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_raw(self, data: dict[str, Any]) -> None:
        # atomic: write tmp in same dir, fsync, rename
        fd, tmp = tempfile.mkstemp(prefix=".scratch-", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
