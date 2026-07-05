"""Role assigner — maps a RouterDecision + path to a WorkflowPlan's roles.

Critical invariant: the worker's access_list MUST NOT include the gate definition.
The gate is authored by the orchestrator and read only by the verifier.
"""
from __future__ import annotations

from typing import Any

from orchestrator.workflow import EscalationSpec, GateSpec, RoleSpec, WorkflowPlan

# Default access lists per role (per .sail/rules/memory-isolation.md)
DEFAULT_ACCESS = {
    "orchestrator": ["vision", "state", "scratchpad:meta", "scratchpad:plan"],
    "planner": ["vision", "scratchpad:task", "scratchpad:plan"],
    "worker": ["scratchpad:task", "retrieval:scoped"],
    "verifier": ["scratchpad:task", "artifacts", "gate_output", "gate_definition"],
    "researcher": ["vision", "scratchpad:research", "research/", "memory_search"],
}


class RoleAssigner:
    def __init__(self, routing_config: dict[str, Any]):
        router_cfg = routing_config.get("router", routing_config)
        self.task_types = router_cfg.get("task_types", {})

    def assign(self, decision: Any, task_text: str, gate_command: str = "", gate_description: str = "") -> WorkflowPlan:
        path = decision.recommended_path
        roles: list[RoleSpec] = []

        if path == "research":
            roles.append(RoleSpec(role="worker", agent="researcher", model_role="default", access_list=DEFAULT_ACCESS["researcher"]))
            gate = GateSpec(command=gate_command or "test -f research/report.md", description=gate_description or "research report exists; no production files edited")
        elif path == "specialist":
            roles.append(RoleSpec(role="worker", agent="worker", model_role="default", access_list=DEFAULT_ACCESS["worker"]))
            roles.append(RoleSpec(role="verifier", agent="verifier", model_role="slow", access_list=DEFAULT_ACCESS["verifier"]))
            gate = GateSpec(command=gate_command, description=gate_description)
        elif path == "generalist":
            roles.append(RoleSpec(role="worker", agent="worker", model_role="slow", access_list=DEFAULT_ACCESS["worker"]))
            roles.append(RoleSpec(role="verifier", agent="verifier", model_role="slow", access_list=DEFAULT_ACCESS["verifier"]))
            gate = GateSpec(command=gate_command, description=gate_description, rubric="judge-bounded" if not gate_command else None)
        else:  # worker / parallel
            roles.append(RoleSpec(role="worker", agent="worker", model_role=decision.model_role, access_list=DEFAULT_ACCESS["worker"]))
            roles.append(RoleSpec(role="verifier", agent="verifier", model_role="slow", access_list=DEFAULT_ACCESS["verifier"]))
            gate = GateSpec(command=gate_command, description=gate_description)

        return WorkflowPlan(
            path=path,
            roles=roles,
            gate=gate,
            escalation=EscalationSpec(on_fail="generalist", max_retries=2),
            notes=f"router: {decision.task_type} conf={decision.confidence}",
        )
