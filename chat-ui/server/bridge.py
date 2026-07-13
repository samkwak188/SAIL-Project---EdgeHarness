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
_config_file = DEFAULT_CONFIG


def get_platform() -> dict[str, Any]:
    global _platform
    if _platform is None:
        os.chdir(SAIL_ROOT)  # file tools resolve relative paths against CWD
        _platform = _build_platform(root=SAIL_ROOT, models_cfg_path=SAIL_ROOT / _config_file)
    return _platform


# ----- model configs + add-key flow -----

PROVIDERS = {
    "openrouter": {
        "prefix": "sk-or-",
        "env": "OPENROUTER_API_KEY",
        "verify_model": "openrouter/google/gemma-4-31b-it",
        "config": "config/models.openrouter.yaml",
        "provider_block": {"gemma4_31b": {"type": "openrouter", "model": "google/gemma-4-31b-it"}},
    },
    "anthropic": {
        "prefix": "sk-ant-",
        "env": "ANTHROPIC_API_KEY",
        "verify_model": "anthropic/claude-haiku-4-5",
        "config": "config/models.anthropic.yaml",
        "provider_block": {"claude_haiku": {"model": "anthropic/claude-haiku-4-5"}},
    },
    "google": {
        "prefix": "AIza",
        "env": "GEMINI_API_KEY",
        "verify_model": "gemini/gemini-2.5-flash",
        "config": "config/models.google.yaml",
        "provider_block": {"gemini_flash": {"model": "gemini/gemini-2.5-flash"}},
    },
}


def detect_provider(api_key: str) -> str | None:
    for name, info in PROVIDERS.items():
        if api_key.startswith(info["prefix"]):
            return name
    return None


def list_configs() -> list[dict[str, Any]]:
    import yaml
    out = []
    for p in sorted((SAIL_ROOT / "config").glob("models*.yaml")):
        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        providers = [
            {"name": name, "model": prov.get("model", name)}
            for name, prov in cfg.get("providers", {}).items()
        ]
        rel = f"config/{p.name}"
        out.append({"file": rel, "providers": providers, "active": rel == _config_file})
    return out


def select_config(file: str) -> bool:
    global _config_file, _platform
    if not (SAIL_ROOT / file).exists():
        return False
    _config_file = file
    _platform = None  # rebuilt lazily with the new config
    return True


def add_key(api_key: str) -> dict[str, Any]:
    """Detect provider by prefix, 1-token verify ping, persist to .env + models yaml."""
    provider = detect_provider(api_key.strip())
    if provider is None:
        return {"ok": False, "error": "unrecognized key prefix (expected sk-or- / sk-ant- / AIza)"}
    info = PROVIDERS[provider]

    prev = os.environ.get(info["env"])
    os.environ[info["env"]] = api_key.strip()
    try:
        import litellm
        litellm.completion(model=info["verify_model"], messages=[{"role": "user", "content": "hi"}], max_tokens=1)
    except Exception as e:
        if prev is None:
            os.environ.pop(info["env"], None)
        else:
            os.environ[info["env"]] = prev
        return {"ok": False, "error": f"key verification failed: {e}"}

    _write_env_var(info["env"], api_key.strip())
    _ensure_config(provider)
    return {"ok": True, "provider": provider, "config": info["config"]}


def _write_env_var(var: str, value: str) -> None:
    env_path = SAIL_ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    lines = [ln for ln in lines if not ln.startswith(f"{var}=")]
    lines.append(f"{var}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ensure_config(provider: str) -> None:
    import yaml
    info = PROVIDERS[provider]
    path = SAIL_ROOT / info["config"]
    if path.exists():
        return
    first = next(iter(info["provider_block"]))
    cfg = {
        "providers": info["provider_block"],
        "embedding": {"provider": "fastembed", "model": "BAAI/bge-small-en-v1.5", "dim": 384},
        "role_mapping": {role: [first] for role in ("smol", "default", "slow", "plan", "judge")},
    }
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")


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
