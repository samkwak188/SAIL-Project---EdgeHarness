"""sail CLI — entry point that wires the whole platform together.

Commands:
  sail loop --once --dry-run        run one autonomous loop cycle (smoke task)
  sail task run <yaml>              run a specific task from a YAML fixture
  sail memory search <query> -k 5   semantic search over the local corpus
  sail telemetry report             cost/latency rollup
  sail eval readiness-check         is the eval basket committed?
  sail research domain-bakeoff      run the domain bake-off skill (stub)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
import yaml

# Make the sail-platform root importable when run via `python cli.py`
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from harness.context import ContextAssembler, load_agent_spec  # noqa: E402
from harness.loop import HarnessLoop  # noqa: E402
from harness.tools.registry import ToolExecutor, build_default_registry  # noqa: E402
from harness.tools.sandbox import SandboxedBash  # noqa: E402
from memory.embedder import LocalEmbedder  # noqa: E402
from memory.scratchpad import Scratchpad  # noqa: E402
from memory.turbovec_store import TurbovecStore  # noqa: E402
from orchestrator.escalation import ErrorRecoveryLadder, EscalationPolicy  # noqa: E402
from orchestrator.roles import RoleAssigner  # noqa: E402
from orchestrator.router import Router  # noqa: E402
from orchestrator.workflow import WorkflowEngine  # noqa: E402
from providers.litellm_pool import LiteLLMPool  # noqa: E402
from telemetry.recorder import TelemetryRecorder  # noqa: E402
from telemetry.report import report as telemetry_report  # noqa: E402


def _load_yaml(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _load_settings(root: Path) -> dict[str, Any]:
    return _load_yaml(root / ".sail" / "settings.yaml")


def _build_platform(root: Path | None = None, models_cfg_path: str | Path | None = None) -> dict[str, Any]:
    """Wire every component. Returns a dict of wired objects."""
    root = root or _ROOT
    settings = _load_settings(root)

    telemetry = TelemetryRecorder(root / settings.get("telemetry", {}).get("path", "telemetry/runs"))
    scratchpad = Scratchpad(root / settings.get("memory", {}).get("scratchpad_path", ".sail/state/scratchpad.json"))
    models_cfg = _load_yaml(models_cfg_path or (root / "config" / "models.yaml"))
    embedder = LocalEmbedder(
        model=models_cfg.get("embedding", {}).get("model", "BAAI/bge-small-en-v1.5"),
        dim=settings.get("memory", {}).get("turbovec", {}).get("dim", 384),
    )
    store = TurbovecStore(
        dim=settings["memory"]["turbovec"]["dim"],
        bit_width=settings["memory"]["turbovec"]["bit_width"],
        index_path=str(root / settings["memory"]["turbovec"]["index_path"]),
    )
    provider = LiteLLMPool(models_cfg)
    routing_cfg = _load_yaml(root / "config" / "routing.yaml")
    router = Router(routing_cfg, embedder=embedder, telemetry=telemetry)
    role_assigner = RoleAssigner(routing_cfg)
    escalation = EscalationPolicy(telemetry=telemetry)
    ladder = ErrorRecoveryLadder(max_retries_per_step=settings["harness"]["max_retries_per_step"], telemetry=telemetry)

    ctx_asm = ContextAssembler(root / ".sail", settings)
    for name, schema in build_default_registry().items():
        ctx_asm.register_tool(name, schema)

    sandbox = SandboxedBash(
        mode=settings["harness"]["sandbox"]["bash"],
        denylist=settings["harness"]["sandbox"]["denylist"],
        cwd=str(root),
    )

    return {
        "root": root,
        "settings": settings,
        "telemetry": telemetry,
        "scratchpad": scratchpad,
        "embedder": embedder,
        "store": store,
        "provider": provider,
        "router": router,
        "role_assigner": role_assigner,
        "escalation": escalation,
        "ladder": ladder,
        "ctx_asm": ctx_asm,
        "sandbox": sandbox,
    }


def _make_tool_executor(role: str, platform: dict[str, Any], plan=None) -> ToolExecutor:
    hooks = {
        "pre_bash": [lambda c: (True, "")],  # denylist already enforced in SandboxedBash
        "post_edit": [],  # LSP hook can be added when an LSP is available
    }

    def spawn_fn(agent_name: str, model_role: str, task: str, access_list: list[str], task_id: str = "") -> dict[str, Any]:
        return _spawn_agent(agent_name, model_role, task, access_list, task_id or "spawn", platform, plan)

    def route_fn(task_text: str) -> dict[str, Any]:
        d = platform["router"].route(task_text)
        return d.__dict__

    # state_writer is only enabled for the verifier role
    state_writer = _StateWriter(platform["root"] / ".sail" / "STATE.md") if role == "verifier" else None

    return ToolExecutor(
        role=role,
        scratchpad=platform["scratchpad"],
        memory_store=_MemoryAdapter(platform["store"], platform["embedder"]),
        sandbox=platform["sandbox"],
        state_writer=state_writer,
        spawn_fn=spawn_fn if role == "orchestrator" else None,
        route_fn=route_fn if role == "orchestrator" else None,
        hooks=hooks,
    )


class _StateWriter:
    """Updates STATE.md — verifier-only path to Done."""

    def __init__(self, path: Path):
        self.path = path

    def update(self, item_id: str, status: str, evidence: str = "", role: str = "verifier") -> None:
        if role != "verifier":
            raise PermissionError(f"only verifier may update STATE, got {role}")
        text = self.path.read_text(encoding="utf-8")
        # very small markdown state machine
        if status == "done":
            text = text.replace(f"- [ ] [{item_id}]", f"- [x] [{item_id}]")  # mark done
            text = text.replace("## Done   <!-- only verifier moves items here, with evidence -->\n- (none yet)",
                                f"## Done   <!-- only verifier moves items here, with evidence -->\n- [x] [{item_id}] — {evidence[:120]}")
        self.path.write_text(text, encoding="utf-8")


class _MemoryAdapter:
    """Adapts the TurbovecStore + embedder to the memory_search tool signature."""

    def __init__(self, store: TurbovecStore, embedder: LocalEmbedder):
        self.store = store
        self.embedder = embedder

    def search(self, query: str, k: int = 5, allowlist: list[int] | None = None) -> list[dict[str, Any]]:
        qv = self.embedder.embed(query)
        return self.store.search(qv, k=k, allowlist=allowlist)


def _spawn_agent(agent_name: str, model_role: str, task: str, access_list: list[str], task_id: str, platform: dict[str, Any], plan=None) -> dict[str, Any]:
    """Spawn a child agent in an isolated context, run the harness loop, return its result."""
    agent_spec = load_agent_spec(platform["root"] / ".sail" / "agents" / f"{agent_name}.md")
    agent_spec.model_role = model_role or agent_spec.model_role
    tool_exec = _make_tool_executor(agent_spec.name, platform, plan)
    scratchpad_slice = platform["scratchpad"].slice(access_list, role=agent_spec.name)
    loop = HarnessLoop(agent_spec, platform["ctx_asm"], tool_exec, platform["provider"], platform["telemetry"])
    result = loop.run(task, scratchpad_slice)
    return {
        "agent": agent_spec.name,
        "ok": result.ok,
        "output": result.output,
        "artifacts": f"scratchpad:task/{task_id}",
        "tool_calls": result.tool_calls,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost": result.cost_estimate,
        "elapsed_ms": result.elapsed_ms,
    }


def _make_spawn_fn(platform: dict[str, Any], plan, task_id: str):
    """Build a spawn_fn closure matching WorkflowEngine's 5-arg call signature."""
    def spawn_fn(agent_name: str, model_role: str, task: str, access_list: list[str], _tid: str = "") -> dict[str, Any]:
        return _spawn_agent(agent_name, model_role, task, access_list, _tid or task_id, platform, plan)
    return spawn_fn


# ----- CLI -----

@click.group()
def cli() -> None:
    """sail — local AI orchestrator + harness loop."""


@cli.command("loop")
@click.option("--once", is_flag=True, help="run exactly one cycle")
@click.option("--dry-run", is_flag=True, help="don't actually spawn model calls; structural check only")
@click.option("--config", "config_path", default=None, help="path to a models config YAML (default: config/models.yaml)")
def cmd_loop(once: bool, dry_run: bool, config_path: str | None) -> None:
    """Run one autonomous loop cycle."""
    platform = _build_platform(models_cfg_path=config_path)
    root = platform["root"]
    # pick the highest-priority Open item from STATE.md (very simple parser)
    state_text = (root / ".sail" / "STATE.md").read_text(encoding="utf-8")
    open_item = _first_open_item(state_text)
    if open_item is None:
        click.echo("no open items in STATE.md — nothing to do")
        return
    item_id, desc = open_item
    click.echo(f"[loop] picked open item: {item_id} — {desc}")
    task_text = _resolve_task_text(desc, root)
    if task_text != desc:
        click.echo(f"[loop] resolved task_text: {task_text[:80]}")

    decision = platform["router"].route(task_text, task_id=item_id)
    click.echo(f"[loop] router: type={decision.task_type} conf={decision.confidence} path={decision.recommended_path}")

    if dry_run:
        click.echo("[loop] dry-run: not spawning agents. Telemetry + decision logged.")
        platform["telemetry"].close()
        return

    plan = platform["role_assigner"].assign(decision, task_text)
    engine = WorkflowEngine(
        platform["telemetry"],
        _StateWriter(root / ".sail" / "STATE.md"),
        spawn_fn=_make_spawn_fn(platform, plan, item_id),
        sandbox=platform["sandbox"],
    )
    result = engine.execute(plan, task_text)
    click.echo(json.dumps(result, indent=2, default=str))
    platform["telemetry"].close()


@cli.command("task")
@click.argument("subcommand")
@click.argument("yaml_path", required=False)
@click.option("--config", "config_path", default=None, help="path to a models config YAML (default: config/models.yaml)")
def cmd_task(subcommand: str, yaml_path: str | None, config_path: str | None) -> None:
    """Run a specific task from a YAML fixture."""
    if subcommand != "run" or not yaml_path:
        click.echo("usage: sail task run <yaml>")
        return
    platform = _build_platform(models_cfg_path=config_path)
    spec = _load_yaml(yaml_path)
    task_text = spec["task_text"]
    click.echo(f"[task] {task_text[:80]}")
    decision = platform["router"].route(task_text)
    click.echo(f"[task] router: type={decision.task_type} conf={decision.confidence} path={decision.recommended_path}")
    plan = platform["role_assigner"].assign(decision, task_text, gate_command=spec.get("gate", {}).get("command", ""), gate_description=spec.get("gate", {}).get("description", ""))
    engine = WorkflowEngine(
        platform["telemetry"],
        _StateWriter(platform["root"] / ".sail" / "STATE.md"),
        spawn_fn=_make_spawn_fn(platform, plan, plan.task_id),
        sandbox=platform["sandbox"],
    )
    result = engine.execute(plan, task_text)
    click.echo(json.dumps(result, indent=2, default=str))
    platform["telemetry"].close()


@cli.command("memory")
@click.argument("subcommand")
@click.argument("query", required=False)
@click.option("-k", default=5)
def cmd_memory(subcommand: str, query: str | None, k: int) -> None:
    """Memory operations."""
    if subcommand != "search" or not query:
        click.echo("usage: sail memory search <query> -k 5")
        return
    platform = _build_platform()
    qv = platform["embedder"].embed(query)
    hits = platform["store"].search(qv, k=k)
    click.echo(json.dumps(hits, indent=2, default=str))


@cli.command("telemetry")
@click.argument("subcommand")
def cmd_telemetry(subcommand: str) -> None:
    """Telemetry operations."""
    if subcommand != "report":
        click.echo("usage: sail telemetry report")
        return
    platform = _build_platform()
    click.echo(json.dumps(telemetry_report(platform["root"] / "telemetry" / "runs"), indent=2))


@cli.command("eval")
@click.argument("subcommand")
def cmd_eval(subcommand: str) -> None:
    """Eval harness operations (stub until domain bake-off completes)."""
    from eval.interface import EvalHarness

    if subcommand == "readiness-check":
        ok = EvalHarness().readiness_check()
        click.echo("READY" if ok else "NOT_READY — run `sail research domain-bakeoff` first")
        sys.exit(0 if ok else 1)
    click.echo(f"eval {subcommand} not implemented yet (stub)")


@cli.command("research")
@click.argument("subcommand")
def cmd_research(subcommand: str) -> None:
    """Research operations."""
    if subcommand == "domain-bakeoff":
        click.echo("domain-bakeoff skill — see .sail/skills/domain-bakeoff/SKILL.md")
        click.echo("Phase A (research) is automated; Phases B/C require human outreach + approval.")
        click.echo("Run `sail task run examples/smoke_research.yaml` to kick off Phase A.")
        return
    click.echo(f"research {subcommand} not implemented")


def _first_open_item(state_text: str) -> tuple[str, str] | None:
    """Find the first '- [ ] [item-id] description' line in STATE.md.

    Format: `- [ ] [item-id] description...`
    The first `[ ]` is the checkbox; the SECOND `[...]` is the item id.
    """
    for line in state_text.splitlines():
        line = line.strip()
        if not line.startswith("- [ ] "):
            continue
        rest = line[len("- [ ] "):]
        if not rest.startswith("[") or "]" not in rest:
            continue
        try:
            id_end = rest.index("]")
            item_id = rest[1:id_end]
            desc = rest[id_end + 1 :].strip(" -")
            return item_id, desc
        except Exception:
            continue
    return None


def _resolve_task_text(desc: str, root: Path) -> str:
    """If an open item references a YAML in examples/, load its task_text."""
    import re

    # Match either "examples/foo.yaml" or bare "foo.yaml" (try examples/ prefix)
    m = re.search(r"((?:examples/)?[A-Za-z0-9_/-]+\.yaml)", desc)
    if m:
        candidate = m.group(1)
        for p in [root / candidate, root / "examples" / candidate]:
            if p.exists():
                spec = _load_yaml(p)
                return spec.get("task_text", desc)
    return desc


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
