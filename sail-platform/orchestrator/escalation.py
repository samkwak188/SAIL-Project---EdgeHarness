"""Escalation policy + 4-rung error-recovery ladder.

Rungs (per step, bounded by max_retries_per_step):
  1. Error-guided retry  — feed verbatim error back to same agent
  2. Format fallback    — switch edit format (str_replace → whole_file)
  3. Tier escalation    — re-run step on next model rung (smol → default → slow)
  4. Block + report     — move to Blocked in STATE with full failure trail

Never skip a rung; never weaken a gate; never retry past max without escalating.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TIER_LADDER = ["smol", "default", "slow"]


@dataclass
class EscalationEvent:
    task_id: str
    step_id: str
    rung: int
    trigger: str
    from_tier: str
    to_tier: str


class ErrorRecoveryLadder:
    def __init__(self, max_retries_per_step: int = 2, telemetry: Any | None = None):
        self.max_retries = max_retries_per_step
        self.telemetry = telemetry

    def next_rung(self, current_rung: int, current_tier: str, error: str) -> tuple[int, str, str] | None:
        """Return (new_rung, new_tier, action) or None if past max → block."""
        if current_rung >= 3:
            return None  # block

        if current_rung == 0:
            # rung 1: error-guided retry on same tier
            return (1, current_tier, "error_guided_retry")
        if current_rung == 1:
            # rung 2: format fallback on same tier
            return (2, current_tier, "format_fallback")
        if current_rung == 2:
            # rung 3: tier escalation
            try:
                idx = TIER_LADDER.index(current_tier)
            except ValueError:
                idx = 1
            if idx + 1 < len(TIER_LADDER):
                new_tier = TIER_LADDER[idx + 1]
                return (3, new_tier, "tier_escalation")
            return None  # no higher tier → block
        return None


class EscalationPolicy:
    """Decides whether to escalate the whole task (vs. recover a single step)."""

    def __init__(self, telemetry: Any | None = None):
        self.telemetry = telemetry

    def should_escalate_task(self, decision: Any, novel_distance: float | None = None) -> bool:
        if decision.confidence < 0.75:
            return True
        if novel_distance is not None and novel_distance < 0.5:
            return True
        return False

    def record(self, evt: EscalationEvent) -> None:
        if self.telemetry is None:
            return
        self.telemetry.record_escalation(evt.task_id, evt.trigger, evt.from_tier, evt.to_tier, evt.rung)
