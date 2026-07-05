"""eval package — stub; activates after domain bake-off.

Implements HARNESS_RESEARCH_GUIDE.md methodology:
  - test-scored ground truth (never eye/LLM-judge for primary result)
  - paired configs (same fixed task subset)
  - >=3 runs, mean ± CI
  - McNemar's test on paired per-task pass/fail
  - pin everything (model versions, harness commit, benchmark commit)
"""
from eval.interface import EvalHarness, TaskBasket
from eval.scoreboard import Scoreboard

__all__ = ["EvalHarness", "TaskBasket", "Scoreboard"]
