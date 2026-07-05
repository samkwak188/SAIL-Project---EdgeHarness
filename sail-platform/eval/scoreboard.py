"""Scoreboard — weekly KPI gate (stub)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Scoreboard:
    week: int
    configs: list[dict[str, Any]]
    headline_metric: str = "success_rate"
    gated_pass: bool = False

    @classmethod
    def from_reports(cls, reports: list[Any], week: int) -> Scoreboard:
        if not reports:
            return cls(week=week, configs=[], gated_pass=False)
        best = max(r.success_rate for r in reports)
        return cls(week=week, configs=[r.config for r in reports], gated_pass=best >= 0.5)
