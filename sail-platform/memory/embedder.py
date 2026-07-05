"""Local embedder — bge/e5-class via fastembed.

Fully local (per the on-prem premise). Never a cloud embedding API.
Dim must match settings.memory.turbovec.dim and config/models.yaml embedding.dim.
"""
from __future__ import annotations


class LocalEmbedder:
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5", dim: int = 384):
        self.model_name = model
        self.dim = dim
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        try:
            from fastembed import TextEmbedding  # type: ignore

            self._model = TextEmbedding(model_name=self.model_name)
        except ImportError:  # pragma: no cover
            self._model = None  # tests will use a stub

    def embed(self, text: str) -> list[float]:
        self._load()
        if self._model is None:
            # deterministic stub for tests — hashes to dim floats
            return self._stub_embed(text)

        vecs = list(self._model.embed([text]))
        v = vecs[0]
        return list(map(float, v))

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._load()
        if self._model is None:
            return [self._stub_embed(t) for t in texts]
        vecs = list(self._model.embed(texts))
        return [list(map(float, v)) for v in vecs]

    def _stub_embed(self, text: str) -> list[float]:
        import hashlib
        import struct

        out = []
        seed = text.encode("utf-8")
        for i in range(self.dim):
            h = hashlib.md5(seed + i.to_bytes(4, "big")).digest()
            (val,) = struct.unpack("f", h[:4])
            out.append(float(val % 1.0))
        return out
