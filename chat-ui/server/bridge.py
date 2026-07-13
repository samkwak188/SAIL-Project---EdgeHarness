"""Bridge: sail-platform harness -> event queue for the SSE API.

Wraps cli._build_platform(); v1 chat depth is router + worker loop (no gate).
Event vocabulary (AG-UI-shaped): router_decision, turn_start, tool_call_start,
tool_result, answer, usage, error.
"""
from __future__ import annotations

import os
import queue
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SAIL_ROOT = REPO_ROOT / "sail-platform"
if str(SAIL_ROOT) not in sys.path:
    sys.path.insert(0, str(SAIL_ROOT))

from cli import _build_platform, _make_tool_executor  # noqa: E402
from harness.context import load_agent_spec  # noqa: E402
from harness.loop import HarnessLoop  # noqa: E402

DEFAULT_CONFIG = "config/models.openrouter.yaml"

_platform: dict[str, Any] | None = None


def get_platform() -> dict[str, Any]:
    global _platform
    if _platform is None:
        os.chdir(SAIL_ROOT)  # file tools resolve relative paths against CWD
        _platform = _build_platform(root=SAIL_ROOT, models_cfg_path=SAIL_ROOT / DEFAULT_CONFIG)
    return _platform


def run_chat(message: str, q: queue.Queue) -> None:
    """Run one chat turn, pushing {type, data} events onto q. None = end sentinel.

    Blocking — run in a worker thread.
    """
    def emit(event: str, data: dict[str, Any]) -> None:
        q.put({"type": event, "data": data})

    try:
        p = get_platform()
        decision = p["router"].route(message)
        emit("router_decision", {
            "task_type": decision.task_type,
            "confidence": decision.confidence,
            "path": decision.recommended_path,
        })

        spec = load_agent_spec(SAIL_ROOT / ".sail" / "agents" / "worker.md")
        tools = _make_tool_executor("worker", p)
        loop = HarnessLoop(spec, p["ctx_asm"], tools, p["provider"], p["telemetry"], on_event=emit)
        result = loop.run(message, p["scratchpad"].slice([], role="worker"))

        emit("answer", {"text": result.output, "ok": result.ok, "error": result.error})
        emit("usage", {
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost": result.cost_estimate,
            "elapsed_ms": result.elapsed_ms,
        })
    except Exception as e:
        emit("error", {"message": str(e)})
    finally:
        q.put(None)
