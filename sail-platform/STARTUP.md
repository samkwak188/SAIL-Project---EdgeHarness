# sail-platform — Startup Guide

## Prerequisites
- Python 3.10+ (tested with 3.11)
- A model server (vLLM/SGLang on GPU, or Ollama on edge) — OR use the stub config for dev

## Install
```bash
cd sail-platform
python3.11 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pip install pytest  # for the smoke gate
```

## Run

### Dry-run loop (structural check, no model calls)
```bash
.venv/bin/python cli.py loop --once --dry-run
```

### Full E2E task (stub providers — no model server needed)
```bash
.venv/bin/python cli.py task run examples/smoke_coding.yaml --config config/models.dev.yaml
```

### Full E2E task (real model server)
```bash
# 1. Start vLLM on GPU: vllm serve qwen3-72b-awq --port 8000
# 2. Start Ollama on edge: ollama pull qwen3-8b && ollama serve
# 3. Run with the real config:
.venv/bin/python cli.py task run examples/smoke_coding.yaml
```

### Memory search
```bash
.venv/bin/python cli.py memory search "vector quantization" -k 5
```

### Telemetry report
```bash
.venv/bin/python cli.py telemetry report
```

### Eval readiness check
```bash
.venv/bin/python cli.py eval readiness-check
# exits 0 when domain basket is committed; 1 otherwise
```

## Verified success criteria (2026-07-05)
1. `.sail/` harness folder complete: VISION, STATE, settings.yaml, 5 agents, 4 skills, 2 rules
2. End-to-end loop: router → worker → verifier → STATE, with sandboxed gate execution
3. Telemetry stream live: per-call JSONL (tokens, latency, cost, route, gate result)
4. Router v0 (keywords + embedding) routes smoke tasks correctly; decisions logged
5. Error-recovery ladder: 4 rungs (retry → format fallback → tier escalate → block)
6. Hybrid model pool: 5 roles (smol/default/slow/plan/judge) on GPU + edge providers
7. turbovec memory with local embedder (bge-small, d=384) — dims match
8. Eval harness stub with activation checklist; readiness-check returns NOT_READY
9. Domain bake-off skill exists at `.sail/skills/domain-bakeoff/SKILL.md`
10. Three smoke fixtures: smoke_coding, smoke_knowledge, smoke_research

## Next steps (post-architecture)
- Run `sail research domain-bakeoff` to pick the eval domain
- Commit `eval/domains/basket.yaml` (2 verifiable + 1 subjective task types)
- Run `sail eval readiness-check` to confirm
- Train router v1 head on the logged decisions (Phase 6)
- Train LoRA specialists for the verifiable task types

## Architecture decisions documented in the plan
- Plan file: `../.cursor/plans/local_ai_orchestrator_6e0c061d.plan.md`
- Two-tier verifier: deterministic gate first, LLM judge only for subjective tasks
- Gate integrity: worker access list excludes gate definition; verifier runs it verbatim
- Memory isolation: per-role access lists enforced by `memory/isolation.py`
- Structured output: guided JSON at the sampler + json_repair fallback (never strict JSON from local models)
- Concurrency: file-locked atomic scratchpad writes; namespaced per-step keys
