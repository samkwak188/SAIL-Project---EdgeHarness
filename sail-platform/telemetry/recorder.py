"""Per-call JSONL telemetry recorder.

One line per model call: {ts, task_id, agent, model_role, provider, turn,
tokens_in, tokens_out, latency_ms, cost, router_decision, gate_result, retry_rung}.

This single stream feeds three consumers:
  1. cost model — $/task and tokens/solved-task (v2 plan §5)
  2. router-v1 training set — features + outcomes
  3. eval scoreboard — weekly KPI gates

Built day 1 because it cannot be retrofitted.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


class TelemetryRecorder:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.run_id = f"run-{uuid.uuid4().hex[:8]}"
        self.file = self.path / f"{self.run_id}.jsonl"
        # open in append; line-buffered so a crash never loses data
        self._fh = self.file.open("a", encoding="utf-8", buffering=1)
        self._fh.write(json.dumps({"event": "run_start", "ts": _now(), "run_id": self.run_id}) + "\n")

    def record_call(
        self,
        agent: str,
        model_role: str,
        turn: int,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        cost: float,
        response_preview: str = "",
        provider: str = "",
        task_id: str = "",
    ) -> None:
        event = {
            "event": "model_call",
            "ts": _now(),
            "task_id": task_id,
            "agent": agent,
            "model_role": model_role,
            "provider": provider,
            "turn": turn,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "cost": cost,
            "response_preview": response_preview,
        }
        self._fh.write(json.dumps(event) + "\n")

    def record_router(self, task_id: str, task_text: str, decision: dict[str, Any]) -> None:
        self._fh.write(json.dumps({
            "event": "router_decision",
            "ts": _now(),
            "task_id": task_id,
            "task_text": task_text[:200],
            "decision": decision,
        }) + "\n")

    def record_gate(self, task_id: str, exit_code: int, command: str, verdict: str, evidence: str = "") -> None:
        self._fh.write(json.dumps({
            "event": "gate_result",
            "ts": _now(),
            "task_id": task_id,
            "command": command,
            "exit_code": exit_code,
            "verdict": verdict,
            "evidence": evidence[:300],
        }) + "\n")

    def record_escalation(self, task_id: str, trigger: str, from_tier: str, to_tier: str, rung: int) -> None:
        self._fh.write(json.dumps({
            "event": "escalation",
            "ts": _now(),
            "task_id": task_id,
            "trigger": trigger,
            "from_tier": from_tier,
            "to_tier": to_tier,
            "rung": rung,
        }) + "\n")

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.write(json.dumps({"event": "run_end", "ts": _now(), "run_id": self.run_id}) + "\n")
            self._fh.close()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())
