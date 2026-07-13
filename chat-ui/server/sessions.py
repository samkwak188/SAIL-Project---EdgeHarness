"""JSON-file session store — one file per session in chat-ui/sessions/ (gitignored)."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

SESSIONS_DIR = Path(__file__).resolve().parents[1] / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


def _path(sid: str) -> Path:
    return SESSIONS_DIR / f"{sid}.json"


def create(title: str = "") -> dict[str, Any]:
    session = {
        "id": uuid.uuid4().hex[:12],
        "title": title or "New session",
        "pinned": False,
        "created": time.time(),
        "updated": time.time(),
        "messages": [],
    }
    _save(session)
    return session


def get(sid: str) -> dict[str, Any] | None:
    p = _path(sid)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def list_sessions() -> list[dict[str, Any]]:
    out = []
    for p in SESSIONS_DIR.glob("*.json"):
        s = json.loads(p.read_text(encoding="utf-8"))
        out.append({k: s[k] for k in ("id", "title", "pinned", "created", "updated")})
    return sorted(out, key=lambda s: s["updated"], reverse=True)


def append(sid: str, entry: dict[str, Any]) -> None:
    session = get(sid)
    if session is None:
        return
    session["messages"].append(entry)
    session["updated"] = time.time()
    _save(session)


def set_pinned(sid: str, pinned: bool) -> None:
    session = get(sid)
    if session is None:
        return
    session["pinned"] = pinned
    _save(session)


def _save(session: dict[str, Any]) -> None:
    _path(session["id"]).write_text(json.dumps(session, indent=2), encoding="utf-8")
