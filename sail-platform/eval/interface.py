"""Eval harness interface — stub with documented activation checklist.

Activate only after the domain bake-off commits config/eval/domains/basket.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskBasket:
    name: str
    task_types: list[dict[str, Any]] = field(default_factory=list)
    # Each task_type: {name, verifiable: bool, gate: str, items: [{id, input, expected}]}


@dataclass
class EvalReport:
    config: str
    n_runs: int
    success_rate: float
    ci_low: float
    ci_high: float
    per_task: list[dict[str, Any]] = field(default_factory=list)
    cost_per_task: float = 0.0
    cost_per_solved: float = 0.0


class EvalHarness:
    """STUB — methods raise NotImplementedError until the basket is committed."""

    def load_basket(self, path: str) -> TaskBasket:
        raise NotImplementedError(
            "Eval harness activates only after the domain bake-off commits "
            "config/eval/domains/basket.yaml. Run `sail research domain-bakeoff` first."
        )

    def run(self, system_config: dict[str, Any], n_runs: int = 3) -> EvalReport:
        raise NotImplementedError("basket not committed — see domain-bakeoff skill")

    def compare_baselines(self, configs: list[dict[str, Any]]) -> Any:
        raise NotImplementedError("basket not committed")

    def readiness_check(self) -> bool:
        """True iff the basket YAML exists and is non-empty."""
        from pathlib import Path

        p = Path("eval/domains/basket.yaml")
        if not p.exists():
            return False
        try:
            import yaml

            d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return bool(d.get("task_types"))
        except Exception:
            return False
