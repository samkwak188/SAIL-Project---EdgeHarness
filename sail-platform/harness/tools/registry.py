"""Tool registry + executor.

Minimal tool surface per role (harness component #2 — weak models misuse large surfaces).
Schemas defined once; executor dispatches calls and runs pre/post hooks.

Tool permission matrix enforced at execution time:
  - state_update : verifier-only (sole path to Done)
  - spawn_agent  : orchestrator-only
  - route_task   : orchestrator-only
"""
from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.edit_formats import mark_read, str_replace_edit, whole_file_write
from harness.tools.sandbox import SandboxedBash


def _schema(name: str, description: str, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {"type": "object", "properties": params.get("properties", {}), "required": params.get("required", [])},
    }


def build_default_registry() -> dict[str, dict[str, Any]]:
    """Default tool schemas — OpenAI function-calling shape."""
    return {
        "read": _schema(
            "read",
            "Read a file's contents. Marks the file as read so subsequent edits are allowed.",
            {
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        ),
        "write": _schema(
            "write",
            "Write content to a file (whole-file). Use only for new files or as a fallback after str_replace failures.",
            {
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        ),
        "edit": _schema(
            "edit",
            "str_replace edit: replace old_string with new_string. Requires the file to have been read in this session.",
            {
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        ),
        "bash": _schema(
            "bash",
            "Run a shell command in a sandbox. Denylist enforced. Network denied by default.",
            {
                "properties": {"command": {"type": "string"}, "timeout": {"type": "integer", "default": 30}},
                "required": ["command"],
            },
        ),
        "grep": _schema(
            "grep",
            "Search file contents with a regex (ripgrep-backed when available).",
            {
                "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}},
                "required": ["pattern"],
            },
        ),
        "glob": _schema(
            "glob",
            "Find files matching a glob pattern.",
            {
                "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}},
                "required": ["pattern"],
            },
        ),
        "scratchpad_read": _schema(
            "scratchpad_read",
            "Read a key from the shared scratchpad. Key must be within the agent's access list.",
            {"properties": {"key": {"type": "string"}}, "required": ["key"]},
        ),
        "scratchpad_write": _schema(
            "scratchpad_write",
            "Write a value to the shared scratchpad under the agent's namespaced key.",
            {"properties": {"key": {"type": "string"}, "value": {"type": "string"}}, "required": ["key", "value"]},
        ),
        "memory_search": _schema(
            "memory_search",
            "Semantic search over the local corpus (turbovec). Optional allowlist filters by doc id set.",
            {
                "properties": {"query": {"type": "string"}, "k": {"type": "integer", "default": 5}, "allowlist": {"type": "array", "items": {"type": "integer"}}},
                "required": ["query"],
            },
        ),
        "state_update": _schema(
            "state_update",
            "VERIFIER-ONLY. Move an item's status in STATE.md. Sole path to Done.",
            {
                "properties": {"item_id": {"type": "string"}, "status": {"type": "string", "enum": ["done", "blocked", "in_progress"]}, "evidence": {"type": "string"}},
                "required": ["item_id", "status"],
            },
        ),
        "spawn_agent": _schema(
            "spawn_agent",
            "ORCHESTRATOR-ONLY. Spawn a child agent with an isolated context and access list.",
            {
                "properties": {
                    "agent": {"type": "string"},
                    "model_role": {"type": "string"},
                    "task": {"type": "string"},
                    "access_list": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["agent", "task"],
            },
        ),
        "route_task": _schema(
            "route_task",
            "ORCHESTRATOR-ONLY. Classify a task and get a routing recommendation.",
            {"properties": {"task_text": {"type": "string"}}, "required": ["task_text"]},
        ),
    }


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    name: str
    ok: bool
    output: str
    error: str = ""
    blocked: bool = False


class ToolExecutor:
    """Execute tool calls with role-based permission checks + hooks."""

    ROLE_TOOLS = {
        "orchestrator": ["scratchpad_read", "scratchpad_write", "route_task", "spawn_agent"],
        "planner": ["scratchpad_read", "scratchpad_write"],
        "worker": ["read", "edit", "write", "bash", "grep", "glob", "scratchpad_read", "scratchpad_write", "memory_search"],
        "verifier": ["bash", "read", "scratchpad_read", "scratchpad_write", "state_update"],
        "researcher": ["read", "grep", "glob", "scratchpad_read", "scratchpad_write", "memory_search", "write"],
    }

    def __init__(
        self,
        role: str,
        scratchpad: Any,
        memory_store: Any | None = None,
        sandbox: SandboxedBash | None = None,
        state_writer: Any | None = None,
        spawn_fn: Callable[[str, str, str, list[str]], str] | None = None,
        route_fn: Callable[[str], dict[str, Any]] | None = None,
        hooks: dict[str, list[Callable]] | None = None,
    ):
        self.role = role
        self.allowed = set(self.ROLE_TOOLS.get(role, []))
        self.scratchpad = scratchpad
        self.memory = memory_store
        self.sandbox = sandbox or SandboxedBash()
        self.state_writer = state_writer
        self.spawn_fn = spawn_fn
        self.route_fn = route_fn
        self.hooks = hooks or {}

    def execute(self, call: ToolCall) -> ToolResult:
        # permission check
        if call.name not in self.allowed:
            return ToolResult(call.name, ok=False, output="", error=f"tool {call.name} not permitted for role {self.role}")
        # pre-hooks
        for h in self.hooks.get(f"pre_{call.name}", []):
            ok, reason = h(call)
            if not ok:
                return ToolResult(call.name, ok=False, output="", error=f"pre-hook blocked: {reason}", blocked=True)
        result = self._dispatch(call)
        # post-hooks
        for h in self.hooks.get(f"post_{call.name}", []):
            try:
                h(call, result)
            except Exception as e:  # pragma: no cover
                result.error = f"post-hook error: {e}"
        return result

    def _dispatch(self, call: ToolCall) -> ToolResult:
        name = call.name
        a = call.arguments
        try:
            if name == "read":
                p = Path(a["path"])
                mark_read(str(p))
                content = p.read_text(encoding="utf-8") if p.exists() else ""
                return ToolResult(name, ok=True, output=content)
            if name == "write":
                r = whole_file_write(a["path"], a["content"])
                return ToolResult(name, ok=True, output=f"wrote {r.bytes_written} bytes to {r.path}")
            if name == "edit":
                r = str_replace_edit(a["path"], a["old_string"], a["new_string"])
                return ToolResult(name, ok=True, output=f"edited {r.path}")
            if name == "bash":
                r = self.sandbox.run(a["command"], timeout=int(a.get("timeout", 30)))
                out = r.stdout
                if r.stderr:
                    out += f"\n[stderr]\n{r.stderr}"
                return ToolResult(name, ok=r.exit_code == 0, output=out, error=r.stderr, blocked=r.blocked)
            if name == "grep":
                return ToolResult(name, ok=True, output=self._grep(a["pattern"], a.get("path", ".")))
            if name == "glob":
                return ToolResult(name, ok=True, output=self._glob(a["pattern"], a.get("path", ".")))
            if name == "scratchpad_read":
                v = self.scratchpad.read(a["key"], role=self.role)
                return ToolResult(name, ok=v is not None, output=json.dumps(v) if v is not None else "", error="" if v is not None else "key not in access list")
            if name == "scratchpad_write":
                self.scratchpad.write(a["key"], json.loads(a["value"]) if a["value"].strip().startswith(("{", "[")) else a["value"], role=self.role)
                return ToolResult(name, ok=True, output=f"wrote scratchpad:{a['key']}")
            if name == "memory_search":
                if self.memory is None:
                    return ToolResult(name, ok=False, output="", error="memory store not configured")
                hits = self.memory.search(a["query"], k=int(a.get("k", 5)), allowlist=a.get("allowlist"))
                return ToolResult(name, ok=True, output=json.dumps(hits))
            if name == "state_update":
                if self.state_writer is None:
                    return ToolResult(name, ok=False, output="", error="state writer not configured")
                self.state_writer.update(a["item_id"], a["status"], a.get("evidence", ""), role=self.role)
                return ToolResult(name, ok=True, output=f"state {a['item_id']} -> {a['status']}")
            if name == "spawn_agent":
                if self.spawn_fn is None:
                    return ToolResult(name, ok=False, output="", error="spawn_fn not configured")
                child_id = self.spawn_fn(a["agent"], a.get("model_role", "default"), a["task"], a.get("access_list", []))
                return ToolResult(name, ok=True, output=child_id)
            if name == "route_task":
                if self.route_fn is None:
                    return ToolResult(name, ok=False, output="", error="route_fn not configured")
                decision = self.route_fn(a["task_text"])
                return ToolResult(name, ok=True, output=json.dumps(decision))
            return ToolResult(name, ok=False, output="", error=f"unknown tool: {name}")
        except Exception as e:
            return ToolResult(name, ok=False, output="", error=str(e))

    @staticmethod
    def _grep(pattern: str, path: str) -> str:
        try:
            proc = subprocess.run(
                ["rg", "--max-count", "20", "-n", pattern, path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return proc.stdout or proc.stderr
        except FileNotFoundError:
            # fall back to plain grep
            proc = subprocess.run(["grep", "-rn", pattern, path], capture_output=True, text=True, timeout=10)
            return proc.stdout[:4000]

    @staticmethod
    def _glob(pattern: str, path: str) -> str:
        root = Path(path)
        matches = sorted(str(p) for p in root.glob(pattern))[:50]
        return "\n".join(matches)
