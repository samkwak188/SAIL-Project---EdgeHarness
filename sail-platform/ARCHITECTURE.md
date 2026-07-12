# Architecture — sail-platform

Orientation map for anyone (human or coding agent) working on this codebase.
Read this before editing. For project status/roadmap see [../implement.md](../implement.md).

## The one-sentence model

The **Python is the engine**; **`.sail/` is the behavior**. Agent personas, rules,
routing, and constraints live in markdown/YAML config — the Python code just executes
whatever `.sail/` and `config/` describe. When adding behavior, ask first whether it
belongs in config, not code.

## Control flow (what happens on `sail task run <yaml>`)

```
cli.py::_build_platform()        wires every component together
        │
        ▼
router.route(task_text)          classify: keyword 0.4 + embedding 0.6, threshold 0.75
        │                        → RouterDecision{task_type, confidence, recommended_path}
        ▼
roles.py::RoleAssigner.assign()  decision → WorkflowPlan{roles, access_lists, gate}
        │                        (worker's access_list EXCLUDES the gate definition)
        ▼
workflow.py::WorkflowEngine.execute()
        │
        ├─ spawn maker (worker)  ──► harness/loop.py::HarnessLoop.run()
        │                              model → tool call → executor → feedback → repeat
        │                              (context assembled by harness/context.py)
        │
        └─ verify (two tiers):
             Tier 1 — deterministic gate: run gate.command in sandbox, exit code = verdict
                      (used when gate.command set AND sandbox present AND no rubric)
             Tier 2 — LLM judge: spawn verifier agent (only when gate.rubric is set)
        │
        ▼
   verdict PASS → verifier writes STATE.md (only the verifier may mark Done)
   verdict FAIL → escalation.py ladder (retry → format-fallback → tier-up → block)
```

## Component map

### Control-flow spine
| File | Responsibility |
|---|---|
| `cli.py` | Entry point + wiring hub. `_build_platform()` instantiates and connects everything. Commands: `loop`, `task run`, `memory search`, `telemetry report`, `eval readiness-check`, `research domain-bakeoff`. |
| `orchestrator/router.py` | Task classification. Blends keyword scores with embedding cosine similarity vs. per-type exemplars; escalates to generalist below `confidence_threshold`. |
| `orchestrator/roles.py` | `RoleAssigner` maps a RouterDecision + path to a `WorkflowPlan` (roles, model tiers, access lists, gate). |
| `orchestrator/workflow.py` | `WorkflowEngine.execute` — spawns maker, runs the two-tier gate, returns the verdict. Also defines the `WorkflowPlan` pydantic models. |
| `orchestrator/escalation.py` | `ErrorRecoveryLadder` (4 rungs) + `EscalationPolicy` (whole-task escalation on low confidence). |

### Harness (the agent runtime)
| File | Responsibility |
|---|---|
| `harness/loop.py` | `HarnessLoop.run` — the model↔tool loop. Builds OpenAI tool-call wire messages (id/type/function + tool_call_id — see gotchas). |
| `harness/context.py` | `ContextAssembler` — 4-layer context (system/message/tools/history). **The single chokepoint enforcing memory isolation.** Parses agent `.md` specs. |
| `harness/tools/registry.py` | Tool schemas (`build_default_registry`) + `ToolExecutor` with the role→tool permission matrix (`ROLE_TOOLS`). |
| `harness/tools/sandbox.py` | `SandboxedBash` — docker (`--network=none`) or subprocess jail, substring denylist. |
| `harness/edit_formats/` | Three edit strategies: `str_replace` (default), `whole_file` (fallback), `patch`. The "ablation dial" for weak-model edit reliability. |

### Supporting subsystems
| File | Responsibility | Real? |
|---|---|---|
| `providers/litellm_pool.py` | Single model interface. Provider types: `stub`, `ollama`, `openrouter`, `openai_compatible` (vLLM/SGLang). Role mapping: smol/default/slow/plan/judge. | ✅ |
| `memory/scratchpad.py` | File-locked atomic JSON scratchpad, role-scoped read/write/slice. | ✅ |
| `memory/turbovec_store.py` | Vector store (turbovec `IdMapIndex`, numpy brute-force fallback). Allowlist filter-then-rerank. | ✅ |
| `memory/embedder.py` | `LocalEmbedder` (fastembed bge-small, dim 384; MD5-hash stub fallback for tests). | ✅ |
| `memory/isolation.py` | `ROLE_ACCESS` table + `enforce_access()` with wildcard matching. | ✅ |
| `telemetry/recorder.py` | JSONL recorder — one line per model call + router/gate/escalation events. | ✅ |
| `telemetry/report.py` | Aggregates run JSONLs into per-agent cost/token/latency + gate/escalation rollup. | ✅ |
| `eval/interface.py` | `EvalHarness` — `readiness_check()` real; `run`/`load_basket`/`compare_baselines` raise NotImplementedError until a basket is committed. | ⚠️ stub |
| `eval/scoreboard.py` | `Scoreboard.from_reports` — success-rate gate (≥0.5). Minimal. | ⚠️ minimal |

### `.sail/` — behavior as config
| Path | What it holds |
|---|---|
| `.sail/settings.yaml` | **Central config**: harness (edit mode, sandbox, retries), context budgets, loop, hooks, memory (turbovec dims), telemetry, isolation access lists. |
| `.sail/VISION.md` | Mission + hard stops (no external network with user data; never weaken gates; only checker marks Done). Injected into every agent's system prompt. |
| `.sail/agents/*.md` | Agent personas. YAML frontmatter (`name`, `model_role`, `tools`) + instruction body. orchestrator/planner/researcher/verifier/worker. |
| `.sail/rules/*.md` | escalation ladder + memory-isolation access table (human-readable specs mirrored by the Python). |
| `.sail/skills/*/SKILL.md` | Task-type playbooks: coding-task, knowledge-task, domain-bakeoff, loop-cycle. |
| `.sail/state/` | Runtime scratchpad JSON (+ lock). |
| `.sail/STATE.md` | The task board (Open/Done/Blocked). Only the verifier moves items to Done. |

### `config/`
| File | What it is |
|---|---|
| `config/models.yaml` | Production: vLLM `gpu_70b` + ollama `edge_8b`. |
| `config/models.dev.yaml` | Stub providers — no network/key needed. **See gotcha #1.** |
| `config/models.openrouter.yaml` | Real inference via OpenRouter (`google/gemma-4-31b-it`). Needs `OPENROUTER_API_KEY` in `.env`. |
| `config/routing.yaml` | 5 task types (coding, extraction, grounded_qa, memo, research) with keywords, exemplars, path, adapter name. |
| `config/mcp_servers.json` | One filesystem server, currently `enabled: false`. Scaffold only. |

## Where do I add X?

| Goal | Touch |
|---|---|
| **New task type** | `config/routing.yaml` — add a type with keywords/exemplars/path/adapter. Router picks it up automatically. |
| **New tool** | `harness/tools/registry.py` — add schema in `build_default_registry`, impl in `ToolExecutor._dispatch`, and grant it in `ROLE_TOOLS` for the roles that should have it. |
| **New agent persona** | `.sail/agents/<name>.md` — frontmatter (`name`/`model_role`/`tools`) + instructions. No Python change. |
| **New model / provider** | `config/models.*.yaml` providers block + role_mapping. Add a case in `litellm_pool.py::_litellm_model_name` only if it's a new provider *type*. |
| **New eval basket** | `eval/domains/basket.yaml` + implement `EvalHarness.run` (currently the P0 blocker — see implement.md). |
| **Change edit reliability behavior** | `.sail/settings.yaml` `harness.edit_mode` / `edit_fallback`. |

## Gotchas (learned the hard way)

1. **Stub mode hides provider-boundary bugs.** `config/models.dev.yaml` never round-trips real tool-call objects — a malformed tool-call message format passed stub tests but 400'd every live provider. **Always test provider/tool-call changes against a real model** (`config/models.openrouter.yaml`), not just stub.
2. **Task runs mutate tracked files.** Running a smoke task edits `examples/fixtures/smoke_coding.py` and appends to `.sail/STATE.md`. `git checkout -- examples/fixtures/smoke_coding.py .sail/STATE.md` after each run to keep the fixture meaningful.
3. **litellm needs the proxy extra for tool calling.** `pip install "litellm[proxy]"` — its tool-call path imports a proxy module chain (fastapi/orjson). Plain `litellm` throws ModuleNotFoundError mid-call.
4. **The gate is two-tier.** Deterministic gate runs ONLY when `gate.command` is set AND a sandbox is present AND `gate.rubric` is unset. Otherwise it spawns an LLM-judge verifier. A task with a `rubric` never runs its `command`.
5. **Only the verifier writes Done.** `state_update` is verifier-only; the worker never marks its own work complete or runs the gate (anti-self-grading).
6. **OpenRouter free tiers rate-limit.** `:free` model slugs 429 constantly upstream — use the paid slug for anything reliable.

## Running it

```bash
source .venv/bin/activate && pip install -e . && pip install "litellm[proxy]"

# stub (no network/key)
python cli.py task run examples/smoke_coding.yaml --config config/models.dev.yaml

# real model (OPENROUTER_API_KEY in .env)
set -a && source .env && set +a
python cli.py task run examples/smoke_coding.yaml --config config/models.openrouter.yaml
```

Smoke tasks: `smoke_coding` (passes; implicit answer key in the pytest gate),
`smoke_research` (structural gate only — currently fails on max_turns),
`smoke_knowledge` (explicit answer key, but its `eval.citation_check` gate module
doesn't exist yet).
