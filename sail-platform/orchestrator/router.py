"""Router v0 — keywords + embedding similarity, with decision logging.

Stages (cheap first):
  1. keyword match — exact signal, fast
  2. embedding similarity — cosine vs task-type exemplars (local embedder)

Every decision is logged via telemetry. This log IS the router-v1 training set.

v1 (post-domain) replaces this with a trained classification head on a frozen
~7B model's hidden states (Fugu technique).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouterDecision:
    task_type: str
    confidence: float
    recommended_path: str       # specialist | generalist | research | parallel | worker
    model_role: str = "default"
    adapter: str | None = None
    stages_run: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)


class Router:
    def __init__(self, routing_config: dict[str, Any], embedder: Any | None = None, telemetry: Any | None = None):
        # routing.yaml nests config under `router:`; accept both shapes for safety
        router_cfg = routing_config.get("router", routing_config)
        self.cfg = router_cfg
        self.threshold = float(router_cfg.get("confidence_threshold", 0.75))
        self.task_types = router_cfg.get("task_types", {})
        self.fallback = routing_config.get("fallback", router_cfg.get("fallback", "generalist"))
        self.embedder = embedder
        self.telemetry = telemetry
        self._exemplar_cache: dict[str, list[Any]] = {}

    def route(self, task_text: str, task_id: str = "") -> RouterDecision:
        scores: dict[str, float] = {}
        stages: list[str] = []

        # Stage 1: keywords
        kw_scores = self._keyword_scores(task_text)
        for t, s in kw_scores.items():
            scores[t] = max(scores.get(t, 0.0), s)
        stages.append("keywords")

        # Stage 2: embedding similarity (only if embedder available and no confident kw hit yet)
        best_kw = max(scores.values()) if scores else 0.0
        if self.embedder is not None and best_kw < self.threshold:
            emb_scores = self._embedding_scores(task_text)
            for t, s in emb_scores.items():
                # weighted combination: 0.4 kw + 0.6 emb if both ran; emb alone if kw empty
                if t in kw_scores and kw_scores[t] > 0:
                    scores[t] = 0.4 * kw_scores[t] + 0.6 * s
                else:
                    scores[t] = max(scores.get(t, 0.0), s)
            stages.append("embedding_similarity")

        if not scores:
            decision = RouterDecision(
                task_type="unknown",
                confidence=0.0,
                recommended_path=self.fallback,
                model_role="slow",
                stages_run=stages,
                scores={},
            )
        else:
            best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
            conf = scores[best_type]
            tt_cfg = self.task_types.get(best_type, {})
            if conf < self.threshold:
                path = self.fallback
                role = "slow"
                adapter = None
            else:
                path = tt_cfg.get("path", self.fallback)
                role = tt_cfg.get("model_role", "default")
                adapter = tt_cfg.get("adapter")
            decision = RouterDecision(
                task_type=best_type,
                confidence=round(conf, 4),
                recommended_path=path,
                model_role=role,
                adapter=adapter,
                stages_run=stages,
                scores={k: round(v, 4) for k, v in scores.items()},
            )

        if self.telemetry is not None:
            self.telemetry.record_router(task_id, task_text, {
                "task_type": decision.task_type,
                "confidence": decision.confidence,
                "path": decision.recommended_path,
                "model_role": decision.model_role,
                "adapter": decision.adapter,
                "stages_run": decision.stages_run,
                "scores": decision.scores,
            })
        return decision

    def _keyword_scores(self, text: str) -> dict[str, float]:
        text_lower = text.lower()
        out: dict[str, float] = {}
        for ttype, cfg in self.task_types.items():
            kws = cfg.get("keywords", [])
            if not kws:
                continue
            hits = sum(1 for k in kws if k.lower() in text_lower)
            if hits:
                out[ttype] = min(1.0, 0.5 + 0.25 * hits)
        return out

    def _embedding_scores(self, text: str) -> dict[str, float]:
        if self.embedder is None:
            return {}
        q = self.embedder.embed(text)
        out: dict[str, float] = {}
        for ttype, cfg in self.task_types.items():
            exemplars = cfg.get("exemplars", [])
            if not exemplars:
                continue
            cached = self._exemplar_cache.get(ttype)
            if cached is None:
                cached = [self.embedder.embed(e) for e in exemplars]
                self._exemplar_cache[ttype] = cached
            best = 0.0
            for ev in cached:
                sim = _cosine(q, ev)
                if sim > best:
                    best = sim
            out[ttype] = max(0.0, best)
        return out


def _cosine(a, b) -> float:
    import numpy as np

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))
