"""WorkflowPlan + WorkflowEngine.

WorkflowPlan is the structured contract the orchestrator emits before spawning
agents. Engine executes it: spawns the maker, runs the gate via the verifier,
applies the escalation policy on failure, updates STATE.

Per the structured-output discipline: agents reason in natural language; the
final WorkflowPlan JSON is produced via guided decoding or json_repair.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from pydantic import BaseModel, Field


class RoleSpec(BaseModel):
    role: str
    agent: str
    model_role: str = "default"
    access_list: list[str] = Field(default_factory=list)


class GateSpec(BaseModel):
    command: str
    description: str = ""
    rubric: str | None = None       # for subjective tasks (judge-bounded)


class EscalationSpec(BaseModel):
    on_fail: str = "generalist"     # generalist | block | retry
    max_retries: int = 2


class WorkflowPlan(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    path: str                       # specialist | generalist | research | parallel | worker
    roles: list[RoleSpec]
    gate: GateSpec
    escalation: EscalationSpec = Field(default_factory=EscalationSpec)
    notes: str = ""


class WorkflowEngine:
    """Execute a WorkflowPlan: maker → gate (verifier) → escalation.

    Two-tier verification (FreePalp pattern):
      1. Deterministic gate — run the gate command directly via SandboxedBash.
         No LLM needed; exit code is the verdict. This is the primary path.
      2. LLM judge — invoked only when gate.rubric is set (subjective tasks,
         no deterministic gate). Different model_role from maker (anti self-grading).
    """

    def __init__(self, telemetry: Any, state_writer: Any, spawn_fn: Any, sandbox: Any = None):
        self.telemetry = telemetry
        self.state_writer = state_writer
        self.spawn_fn = spawn_fn
        self.sandbox = sandbox

    def execute(self, plan: WorkflowPlan, task_text: str) -> dict[str, Any]:
        # spawn maker
        maker = next((r for r in plan.roles if r.role == "worker"), plan.roles[0])
        maker_result = self.spawn_fn(maker.agent, maker.model_role, task_text, maker.access_list, plan.task_id)

        # Tier 1: deterministic gate (run directly if a sandbox is configured)
        verdict = "FAIL"
        exit_code = -1
        gate_stdout = ""
        gate_stderr = ""
        verifier_result: dict[str, Any] = {}

        if plan.gate.command and self.sandbox is not None and not plan.gate.rubric:
            gr = self.sandbox.run(plan.gate.command, timeout=60)
            exit_code = gr.exit_code
            gate_stdout = gr.stdout
            gate_stderr = gr.stderr
            verdict = "PASS" if (gr.exit_code == 0 and not gr.blocked) else "FAIL"
            self.telemetry.record_gate(plan.task_id, exit_code, plan.gate.command, verdict, gate_stdout[:300])
        else:
            # Tier 2: LLM judge (subjective) — spawn verifier agent
            verifier = next((r for r in plan.roles if r.role == "verifier"), None)
            if verifier is None:
                return {"task_id": plan.task_id, "verdict": "NO_VERIFIER", "maker": maker_result}
            verifier_result = self.spawn_fn(
                verifier.agent,
                verifier.model_role,
                json.dumps({"gate": plan.gate.model_dump(), "task_id": plan.task_id, "maker_artifacts": maker_result.get("artifacts")}),
                verifier.access_list,
                plan.task_id,
            )
            verdict = verifier_result.get("verdict", "FAIL")
            exit_code = verifier_result.get("exit_code", -1)
            self.telemetry.record_gate(plan.task_id, exit_code, plan.gate.command, verdict, verifier_result.get("evidence", ""))

        # Update STATE if a state_writer is configured and verdict is PASS
        if self.state_writer is not None and verdict == "PASS":
            try:
                self.state_writer.update(plan.task_id, "done", evidence=f"gate exit {exit_code}", role="verifier")
            except Exception:
                pass

        return {
            "task_id": plan.task_id,
            "verdict": verdict,
            "exit_code": exit_code,
            "gate_stdout": gate_stdout[:500],
            "gate_stderr": gate_stderr[:500],
            "maker": maker_result,
            "verifier": verifier_result,
        }


def parse_plan(raw: str | dict[str, Any]) -> WorkflowPlan:
    """Parse a WorkflowPlan from raw model output.

    Tries strict JSON first; on failure, attempts json_repair; on failure,
    raises. This is the structured-output discipline: agents reason in NL,
    the final JSON is repaired, never demanded strictly from the model.
    """
    if isinstance(raw, dict):
        return WorkflowPlan(**raw)
    try:
        return WorkflowPlan(**json.loads(raw))
    except Exception:
        try:
            from json_repair import repair_json

            repaired = repair_json(raw)
            return WorkflowPlan(**json.loads(repaired))
        except Exception as e:
            raise ValueError(f"could not parse WorkflowPlan: {e}") from e
