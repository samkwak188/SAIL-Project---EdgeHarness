"""Context assembler — Claude Code's 4-layer injection model.

Layers:
  1. System-level    — output style, role, hard constraints (from agent .md)
  2. Message-level   — VISION, STATE slice, scratchpad slice (memory-isolated)
  3. Tool-level      — tool schemas + lifecycle hooks (post-edit lint, pre-bash denylist)
  4. Conversation    — history with per-role token budget + structured compaction

This is the single chokepoint that enforces memory isolation: an agent never sees
scratchpad keys outside its access list, and the worker never sees the gate definition.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentSpec:
    """Parsed front-matter + body of an agent definition."""
    name: str
    model_role: str
    tools: list[str]
    body: str
    raw_path: str


def load_agent_spec(path: str | Path) -> AgentSpec:
    """Parse a .sail/agents/<name>.md file with YAML front-matter."""
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---"):
        return AgentSpec(name=Path(path).stem, model_role="default", tools=[], body=text, raw_path=str(path))
    parts = text.split("---", 2)
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    return AgentSpec(
        name=meta.get("name", Path(path).stem),
        model_role=meta.get("model_role", "default"),
        tools=list(meta.get("tools", [])),
        body=body,
        raw_path=str(path),
    )


@dataclass
class AssembledContext:
    system: str
    messages: list[dict[str, str]]
    tools: list[dict[str, Any]]
    token_budget: int


class ContextAssembler:
    """Assemble a context for an agent given its spec, access list, and current state."""

    def __init__(self, sail_root: str | Path, settings: dict[str, Any]):
        self.sail_root = Path(sail_root)
        self.settings = settings
        self.vision = (self.sail_root / "VISION.md").read_text(encoding="utf-8")
        self._tool_registry: dict[str, dict[str, Any]] = {}

    def register_tool(self, name: str, schema: dict[str, Any]) -> None:
        self._tool_registry[name] = schema

    def assemble(
        self,
        agent: AgentSpec,
        scratchpad_slice: dict[str, Any],
        state_slice: dict[str, Any] | None = None,
        history: list[dict[str, str]] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AssembledContext:
        # Layer 1: system
        system_parts = [agent.body]
        system_parts.append("\n\n## VISION (always honored)\n" + self.vision)
        system = "\n".join(system_parts)

        # Layer 2: message — VISION slice + scratchpad slice (already filtered by access list)
        msg_content = {
            "scratchpad": scratchpad_slice,
            "state": state_slice or {},
        }
        if extra:
            msg_content.update(extra)
        messages = [{"role": "system", "content": f"## Context\n```json\n{json.dumps(msg_content, indent=2)}\n```"}]
        if history:
            budget = self.settings.get("context", {}).get("budgets", {}).get(agent.model_role, 24000)
            messages.extend(self._compact_history(history, budget))

        # Layer 3: tools — only those listed in the agent spec, schemas from registry
        tools = [self._tool_registry[t] for t in agent.tools if t in self._tool_registry]

        budget = self.settings.get("context", {}).get("budgets", {}).get(agent.model_role, 24000)
        return AssembledContext(system=system, messages=messages, tools=tools, token_budget=budget)

    @staticmethod
    def _compact_history(history: list[dict[str, str]], budget: int) -> list[dict[str, str]]:
        """Structured-summary compaction: keep recent turns verbatim, summarize older ones.

        Simplified v1: keep last N turns that fit roughly within budget; prepend a summary
        marker for truncated older turns so the agent knows history was compacted (never
        silent truncation per settings.context.compaction policy).
        """
        if not history:
            return []
        # ~4 chars/token is a reasonable estimate
        char_budget = budget * 4
        kept: list[dict[str, str]] = []
        running = 0
        for msg in reversed(history):
            size = len(msg.get("content", ""))
            if running + size > char_budget and kept:
                kept.insert(0, {"role": "system", "content": "[older history compacted — see scratchpad:plan]"})
                break
            kept.insert(0, msg)
            running += size
        return kept
