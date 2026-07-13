"""The agent loop: model → tool call → executor → feedback → repeat.

Forked from mini-swe-agent's philosophy (minimal, test-scored, domain-agnostic)
with OpenCode-style config and oh-my-pi-style per-role routing added.

Loop invariants:
  - Maker never runs the gate (verifier does, in a fresh context)
  - Edit-format fallback on repeated failures (error-recovery ladder rung 2)
  - Every model call is telemetry-recorded before the result is returned
  - Context is assembled by ContextAssembler which enforces memory isolation
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from harness.context import AgentSpec, ContextAssembler
from harness.tools.registry import ToolCall, ToolExecutor, ToolResult


@dataclass
class StepResult:
    agent: str
    ok: bool
    output: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    elapsed_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_estimate: float = 0.0


@dataclass
class LoopResult:
    task_id: str
    steps: list[StepResult] = field(default_factory=list)
    final_status: str = "pending"  # pending | done | blocked
    elapsed_ms: int = 0
    gate_result: dict[str, Any] | None = None


class HarnessLoop:
    """One agent's inner loop: call model, execute tools, feed back, until done or max_turns."""

    def __init__(
        self,
        agent_spec: AgentSpec,
        context_assembler: ContextAssembler,
        tool_executor: ToolExecutor,
        provider: Any,
        telemetry: Any,
        *,
        max_turns: int = 8,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ):
        self.agent = agent_spec
        self.ctx_asm = context_assembler
        self.tools = tool_executor
        self.provider = provider
        self.telemetry = telemetry
        self.max_turns = max_turns
        self.on_event = on_event

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        """Observer hook for UIs — never allowed to break the loop."""
        if self.on_event is None:
            return
        try:
            self.on_event(event, data)
        except Exception:
            pass

    def run(
        self,
        task: str,
        scratchpad_slice: dict[str, Any],
        state_slice: dict[str, Any] | None = None,
        history: list[dict[str, str]] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> StepResult:
        ctx = self.ctx_asm.assemble(self.agent, scratchpad_slice, state_slice, history, extra)
        messages = list(ctx.messages) + [{"role": "user", "content": task}]
        tool_calls_log: list[dict[str, Any]] = []
        tokens_in = tokens_out = 0
        cost = 0.0
        start = time.time()
        final_output = ""
        ok = True
        err = ""

        for turn in range(self.max_turns):
            self._emit("turn_start", {"agent": self.agent.name, "turn": turn})
            t0 = time.time()
            resp = self.provider.complete(
                system=ctx.system,
                messages=messages,
                tools=ctx.tools,
                model_role=self.agent.model_role,
            )
            t1 = time.time()
            tokens_in += resp.get("tokens_in", 0)
            tokens_out += resp.get("tokens_out", 0)
            cost += resp.get("cost", 0.0)

            self.telemetry.record_call(
                agent=self.agent.name,
                model_role=self.agent.model_role,
                turn=turn,
                tokens_in=resp.get("tokens_in", 0),
                tokens_out=resp.get("tokens_out", 0),
                latency_ms=int((t1 - t0) * 1000),
                cost=resp.get("cost", 0.0),
                response_preview=resp.get("content", "")[:200],
            )

            assistant_msg = resp.get("content", "")
            calls = resp.get("tool_calls", [])
            wire_calls = [
                {
                    "id": c["id"],
                    "type": "function",
                    "function": {"name": c["name"], "arguments": json.dumps(c.get("arguments", {}))},
                }
                for c in calls
            ]
            messages.append({"role": "assistant", "content": assistant_msg, "tool_calls": wire_calls or None})

            if not calls:
                final_output = assistant_msg
                break

            for c in calls:
                tc = ToolCall(name=c["name"], arguments=c.get("arguments", {}))
                self._emit("tool_call_start", {"name": tc.name, "arguments": tc.arguments})
                tr: ToolResult = self.tools.execute(tc)
                self._emit("tool_result", {"name": tc.name, "ok": tr.ok, "output": tr.output[:2000], "error": tr.error})
                tool_calls_log.append({
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "ok": tr.ok,
                    "output": tr.output[:500],
                    "error": tr.error,
                    "blocked": tr.blocked,
                })
                feedback = tr.output if tr.ok else f"ERROR: {tr.error}\n{tr.output}"
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": feedback})
                if not tr.ok and tr.blocked:
                    ok = False
                    err = tr.error
                    break
            if not ok:
                break
        else:
            final_output = final_output or "[max turns reached without final message]"
            ok = False
            err = "max_turns reached"

        return StepResult(
            agent=self.agent.name,
            ok=ok,
            output=final_output,
            tool_calls=tool_calls_log,
            error=err,
            elapsed_ms=int((time.time() - start) * 1000),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_estimate=cost,
        )
