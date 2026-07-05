"""turbovec store — wrapper around turbovec.IdMapIndex with graceful fallback.

If turbovec isn't installed (it's optional), fall back to a brute-force
numpy search. Same public surface so callers don't change.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


class TurbovecStore:
    def __init__(self, dim: int = 384, bit_width: int = 4, index_path: str = "data/index.tvim"):
        self.dim = dim
        self.bit_width = bit_width
        self.index_path = index_path
        self._index = None
        self._ids: list[int] = []
        self._vectors: list[np.ndarray] = []
        self._meta: dict[int, dict[str, Any]] = {}
        self._try_load_turbovec()

    def _try_load_turbovec(self) -> None:
        try:
            from turbovec import IdMapIndex  # type: ignore

            self._index = IdMapIndex(dim=self.dim, bit_width=self.bit_width)
        except ImportError:
            self._index = None  # brute-force fallback

    def add(self, texts: list[str], ids: list[int] | None = None, metas: list[dict[str, Any]] | None = None, embedder: Any | None = None) -> None:
        if embedder is None:
            return
        vecs = embedder.embed_batch(texts)
        if ids is None:
            start = len(self._ids)
            ids = list(range(start, start + len(texts)))
        for i, v, txt in zip(ids, vecs, texts, strict=False):
            v_arr = np.asarray(v, dtype=np.float32)
            self._vectors.append(v_arr)
            self._ids.append(int(i))
            self._meta[int(i)] = {"text": txt, **(metas[i] if metas else {})}
            if self._index is not None:
                try:
                    self._index.add_with_ids(v_arr.reshape(1, -1), np.array([int(i)], dtype=np.uint64))
                except Exception:
                    self._index = None  # fall back

    def search(self, query_vec: list[float], k: int = 5, allowlist: list[int] | None = None) -> list[dict[str, Any]]:
        if not self._vectors:
            return []
        q = np.asarray(query_vec, dtype=np.float32)
        # Filter by allowlist first (the turbovec pattern: external filter → dense rerank)
        candidates = list(range(len(self._ids)))
        if allowlist is not None:
            allowset = set(allowlist)
            candidates = [i for i in range(len(self._ids)) if self._ids[i] in allowset]
        if not candidates:
            return []
        # dense score
        mat = np.stack([self._vectors[i] for i in candidates])
        na = np.linalg.norm(mat, axis=1)
        nq = np.linalg.norm(q)
        if nq == 0 or (na == 0).any():
            sims = np.zeros(len(candidates))
        else:
            sims = (mat @ q) / (na * nq)
        order = np.argsort(-sims)[:k]
        out = []
        for o in order:
            idx = candidates[int(o)]
            doc_id = self._ids[idx]
            out.append({
                "id": doc_id,
                "score": float(sims[o]),
                "meta": self._meta.get(doc_id, {}),
            })
        return out

    def write(self, path: str | None = None) -> None:
        p = Path(path or self.index_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if self._index is not None:
            try:
                self._index.write(str(p))
                return
            except Exception:
                pass
        # fallback: save numpy + meta
        np.save(str(p) + ".npy", np.stack(self._vectors) if self._vectors else np.zeros((0, self.dim), dtype=np.float32))
        import json

        Path(str(p) + ".meta.json").write_text(json.dumps({"ids": self._ids, "meta": self._meta}, default=str), encoding="utf-8")

    def load(self, path: str | None = None) -> None:
        p = Path(path or self.index_path)
        if self._index is not None and Path(str(p)).exists():
            try:
                from turbovec import IdMapIndex  # type: ignore

                self._index = IdMapIndex.load(str(p))
                return
            except Exception:
                pass
        # fallback load
        npy = Path(str(p) + ".npy")
        if npy.exists():
            arr = np.load(str(npy))
            self._vectors = [arr[i] for i in range(len(arr))]
        import json

        meta_p = Path(str(p) + ".meta.json")
        if meta_p.exists():
            d = json.loads(meta_p.read_text(encoding="utf-8"))
            self._ids = d.get("ids", [])
            self._meta = {int(k): v for k, v in d.get("meta", {}).items()}
