# implement.md — status, gaps, and enhancement plan

Handoff document. Everything here was verified by reading the code and running the system
against a live model (2026-07-12), not by trusting README claims. Read alongside
[docs/plan.md](docs/plan.md), [docs/routing.md](docs/routing.md), [docs/testing.md](docs/testing.md).

## 1. Where each plan deliverable actually stands

### 1.1 Harness (agent tool-call loop) — ✅ BUILT, live-verified

`sail-platform/harness/loop.py` runs the model→tool→executor→feedback loop
(mini-swe-agent style, same shape as Claude Code's loop — single agent iterating,
not a multi-agent swarm). `harness/tools/registry.py` implements the tools
(read/write/edit/bash/grep/glob/scratchpad/memory_search) with per-role permission
checks. `orchestrator/workflow.py` wires maker → deterministic sandbox gate →
escalation (4-rung ladder in `orchestrator/escalation.py`, max 2 retries).

Verified today: coding smoke task passes end-to-end on OpenRouter Gemma 4 31B —
model reads the buggy fixture, edits it, pytest gate exits 0. Cost ≈ $0.0009/run.

**Fixed today** (would have blocked any real model, invisible in stub mode):
- `providers/litellm_pool.py::_extract_tool_calls` dropped the tool-call `id` —
  now preserved.
- `harness/loop.py` built assistant/tool messages without the OpenAI wire format
  (`id`/`type`/`function` wrapper, `tool_call_id` on tool responses) — every
  OpenRouter provider 400'd on turn 2. Now emits proper wire format.
- litellm's tool-calling path imports its proxy chain → needs
  `pip install "litellm[proxy]"` (plain `fastapi` alone is not enough).

### 1.2 Router — ✅ v0 BUILT (ahead of plan on breadth)

`orchestrator/router.py::Router.route()`: keyword scores (0.4) blended with
fastembed cosine similarity against per-type exemplars (0.6), compared to
`confidence_threshold: 0.75`; below threshold → generalist path. 5 task types in
`config/routing.yaml` (plan asked for 2–3). Decisions are telemetry-logged, which
doubles as the future training set for the planned v1 trained head. v1 is
deferred work, correctly.

### 1.3 Specialist LoRA adapters — ❌ NOT STARTED (label plumbed, no machinery)

`routing.yaml` carries `adapter: extraction_lora` / `qa_lora` strings;
`RoleAssigner` passes them through `WorkflowPlan`; **`litellm_pool.py` never reads
the field**. No training code, no vLLM multi-LoRA serving flags, nothing greps for
"lora" outside configs/docs.

### 1.4 Ensemble + judge generalist — ❌ NOT STARTED (config-only)

`config/models.yaml` has the `ensemble:` block; `LiteLLMPool.__init__` stores it
as `self.ensemble_cfg`; **no other line in the repo reads `ensemble_cfg`**. The
"generalist" route currently just runs the same single-model worker loop with
`model_role: slow`.

### 1.5 Testing / judge script — ❌ NOT STARTED (stub class)

`eval/interface.py::EvalHarness` — `load_basket`, `run`, `compare_baselines` all
`raise NotImplementedError`. No tokencost dependency, none of the four judge modes
from docs/testing.md (by-reasoning / by-answer / mixed / deterministic) exist in
code. Usable substrate: `telemetry/recorder.py` already captures per-call cost,
latency, and tokens; `eval/scoreboard.py::Scoreboard.from_reports` is a real
reducer awaiting `EvalReport` producers.

### 1.6 Domain basket — ❌ NOT STARTED, **critical-path blocker**

`eval/domains/` contains only a README checklist. `basket.yaml` does not exist;
`sail eval readiness-check` correctly exits 1. Candidates from docs/testing.md:
LegalBench, CUAD. Prior team discussion favored a small hand-built set from
DeWitt's own redacted sample documents over public benchmarks — decide this first.

**Verdict on Sam's work vs. the docs: no pivot.** The architecture matches
plan.md/routing.md exactly; the missing pieces are sequenced-later, not redesigned.
Sam built the chassis first, which was the right order.

## 2. Live-run findings not yet fixed

1. **Research path exhausts its turn budget.** `smoke_research` FAILs with
   "max_turns reached": the researcher burns all turns exploring (read VISION.md
   twice, glob, memory_search) and never writes `research/domains.md`.
   Fix options (either/both): raise `max_turns` for the research path in
   `harness/loop.py` / agent config; add a system-prompt nudge in
   `.sail/agents/researcher.md` to draft output by turn N. Also dedupe repeated
   identical tool calls (read VISION.md ×2) — cheap loop-guard in `loop.py`.
2. **`smoke_knowledge` (specialist path) has never been run live.** Its gate calls
   `python -m eval.citation_check` — verify that module exists before assuming the
   task is runnable.
3. **Task runs mutate tracked files.** Running smoke_coding edits
   `examples/fixtures/smoke_coding.py` and `.sail/STATE.md` in the working tree;
   we `git checkout` them manually each time. The runner should snapshot/restore
   fixtures itself (or copy fixtures to a temp dir and run the gate there).
4. **litellm noise:** stray "Provider List" banners on stderr during runs —
   cosmetic, suppressible via litellm verbosity settings.

## 3. Enhancement plan, prioritized

Ordered by unblock-value. Estimates assume the current codebase conventions.

### P0 — Commit the domain basket (blocks everything measurable)
- Decide domain: DeWitt redacted docs (preferred in prior discussion) vs.
  CUAD/LegalBench subset. If client docs aren't available yet, bootstrap with a
  ~15-item CUAD clause-extraction slice so the eval plumbing can be built, and
  swap the basket contents later — the format is what matters now.
- Write `eval/domains/basket.yaml`: task_text, expected route, gate (deterministic
  where possible), reference answer per item. Mirror the smoke-task YAML shape so
  `WorkflowEngine` can execute basket items unchanged.

### P1 — Implement `EvalHarness.run` + baseline comparison (docs/testing.md)
- `load_basket`: parse basket.yaml → list of tasks.
- `run(config)`: for each item × sample_size, execute via the existing
  `WorkflowEngine`, collect verdict + telemetry (cost/latency/tokens already
  recorded) into `EvalReport`s → `Scoreboard.from_reports`.
- `compare_baselines`: same basket through a cloud model. Cheapest increment: add
  a `claude_baseline` provider entry (litellm handles Anthropic natively), run the
  same loop, diff scoreboards. Add `tokencost` (or litellm's own cost map, already
  partially wired via `response_cost`) for $/task.
- Judge modes: implement **deterministic** (gate-only, no judge) and **by-answer**
  first — they cover extraction/QA. By-reasoning/mixed are later.

### P2 — Ensemble execution for the generalist path
- New `providers/ensemble.py` (or a method on `LiteLLMPool`): fan out
  `ensemble_cfg["candidates"]` completions across `ensemble_cfg["models"]`
  (sequential is fine per the plan's VRAM note), then select: run the existing
  deterministic gate on each candidate if one exists, else a judge call with
  `model_role: judge`. Wire it in `workflow.py` where `path == "generalist"`.
- This makes the "generalist tier" real with ~1 file of code and no training.

### P3 — Adapter serving pass-through (not training)
- In `litellm_pool.py::complete`, when the resolved role/plan carries an
  `adapter`, pass it to the backend (vLLM: `model=<adapter-name>` against a
  server launched with `--lora-modules`; OpenRouter: no-op). This makes the
  specialist tier *servable* the day an adapter exists, decoupled from training.
- Actual LoRA training stays deferred until the basket exposes which task type
  earns an adapter (per plan: 1–2 adapters max in the 4-week scope).

### P4 — Router v1 (only after P0/P1 produce data)
- The telemetry log of routing decisions + gate outcomes is the training set.
  Don't build the trained head before there's real task volume; v0 blending is
  fine for the demo bar.

### P5 — Harness hardening (opportunistic)
- Fixture snapshot/restore in the task runner (finding #3).
- Turn-budget + duplicate-call guard for researcher (finding #1).
- Per-run cost ceiling: abort a task when maker cost exceeds a config cap —
  one guard in `loop.py`, important before basket runs multiply call volume.

## 4. Environment notes

- Real-model config: `sail-platform/config/models.openrouter.yaml`
  (`google/gemma-4-31b-it`, paid tier — the `:free` tier 429s constantly).
  Key lives in `sail-platform/.env` (gitignored), loaded via
  `set -a && source .env && set +a`.
- Target production hardware: Linux boxes, ~128 GB RAM — Gemma 4 31B runs FP16
  (~62 GB) with headroom, so OpenRouter Gemma 4 is a faithful stand-in for the
  eventual local deployment; expect much lower tok/s locally on CPU.
- Stub mode (`config/models.dev.yaml`) needs no network and exercises everything
  except real tool-call round-trips — which is exactly the class of bug it missed;
  don't trust stub-green alone for provider-boundary changes.
