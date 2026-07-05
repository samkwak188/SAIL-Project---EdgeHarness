"""Telemetry report — cost/latency rollup from JSONL runs."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def report(path: str | Path = "telemetry/runs") -> dict[str, Any]:
    """Aggregate every JSONL file in `path` into a cost/latency rollup."""
    p = Path(path)
    if not p.exists():
        return {"total_calls": 0, "total_cost": 0.0, "total_tokens": 0, "by_agent": {}}

    by_agent: dict[str, dict[str, float]] = defaultdict(lambda: {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "latency_ms": 0})
    gates = {"pass": 0, "fail": 0}
    escalations = 0
    total_cost = 0.0
    total_tokens = 0
    total_calls = 0

    for f in p.glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            ev = e.get("event")
            if ev == "model_call":
                a = e["agent"]
                by_agent[a]["calls"] += 1
                by_agent[a]["tokens_in"] += e.get("tokens_in", 0)
                by_agent[a]["tokens_out"] += e.get("tokens_out", 0)
                by_agent[a]["cost"] += e.get("cost", 0.0)
                by_agent[a]["latency_ms"] += e.get("latency_ms", 0)
                total_cost += e.get("cost", 0.0)
                total_tokens += e.get("tokens_in", 0) + e.get("tokens_out", 0)
                total_calls += 1
            elif ev == "gate_result":
                gates["pass" if e.get("verdict") == "PASS" else "fail"] += 1
            elif ev == "escalation":
                escalations += 1

    return {
        "total_calls": total_calls,
        "total_cost": round(total_cost, 4),
        "total_tokens": total_tokens,
        "gates": gates,
        "escalations": escalations,
        "by_agent": {k: {kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in by_agent.items()},
    }
