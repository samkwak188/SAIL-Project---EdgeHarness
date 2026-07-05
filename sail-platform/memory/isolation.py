"""Memory isolation — per-role access lists.

Enforces .sail/rules/memory-isolation.md. The worker cannot see the gate
definition; the verifier can. The orchestrator sees meta + plan, not task
artifacts (which the maker owns).
"""
from __future__ import annotations

# Static defaults — mirror .sail/rules/memory-isolation.md
ROLE_ACCESS = {
    "orchestrator": {
        "read": {"vision", "state", "scratchpad:meta", "scratchpad:plan"},
        "write": {"scratchpad:meta", "scratchpad:plan"},
    },
    "planner": {
        "read": {"vision", "scratchpad:task", "scratchpad:plan"},
        "write": {"scratchpad:plan"},
    },
    "worker": {
        "read": {"scratchpad:task", "retrieval:scoped", "scratchpad:task/*"},
        "write": {"scratchpad:task/*", "artifacts"},
    },
    "verifier": {
        "read": {"scratchpad:task", "artifacts", "gate_output", "gate_definition", "scratchpad:verdict"},
        "write": {"state", "scratchpad:verdict"},
    },
    "researcher": {
        "read": {"vision", "scratchpad:research", "research/", "memory_search"},
        "write": {"research/", "scratchpad:domain_candidates"},
    },
}


def enforce_access(role: str, key: str, write: bool = False) -> bool:
    """Return True if `role` may access `key` (read by default, or write)."""
    if not role:
        return True  # internal caller (e.g. CLI) — unrestricted
    perms = ROLE_ACCESS.get(role)
    if perms is None:
        return False
    allowed = perms["write"] if write else perms["read"] | perms["write"]
    # wildcard support: scratchpad:task/* matches scratchpad:task/step-1
    for pattern in allowed:
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            if key.startswith(prefix):
                return True
        if pattern == key:
            return True
    return False
