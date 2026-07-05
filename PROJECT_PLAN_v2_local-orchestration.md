# Local AI for Knowledge Work — Project Plan v2

**A six-week prototype: a fully-local, on-prem orchestration system that handles a consulting firm's everyday AI work at quality approaching GPT/Claude — with no data leaving the building and no per-query cost.**

Supersedes `Project_Plan.pdf`. This version hardens that plan against four problems (verification/domain mismatch, scope, hardware assumptions, eval credibility) and re-positions it against Sakana Fugu (June 2026).

---

## 0. Thesis (recalibrated and honest)

Sakana **Fugu** (June 22 2026) showed that a *learned orchestrator* coordinating a pool of **frontier cloud models** (Opus 4.8, GPT-5.5, Gemini 3.1) can match or beat any single one. We test the regime Fugu does **not**: a **fully-local, on-prem orchestrator built from open-weight models**, for privacy-constrained knowledge work where cloud frontier models cannot be used at all (data-residency rules, confidential deal data, or — per the June-12 export controls — no frontier access).

The honest claim is **not** "cheap local matches frontier." Fugu reached frontier-plus *because its workers were already frontier* — orchestration rides on top of worker quality, it does not manufacture it. So our claim is bounded and measured:

> A fully-local routed system **matches frontier on the verifiable tasks** where generate-and-verify bites, **approaches it on the subjective tasks**, at **zero per-query cost** and with **no data leaving the building** — and we report the exact gap, not a parity headline.

We do not claim architectural novelty. The router→specialist→ensemble pattern is Fugu's (and the ICLR 2026 TRINITY / Conductor papers'). Our contribution is the **measured local-regime extension**: how far the Fugu idea goes when the pool must be open-weight and on-prem.

---

## 1. What we build (and explicitly not)

A three-tier system organized like a small firm:

- **Router (the manager).** A *trained lightweight classifier* (a head on a frozen small model's hidden states — Fugu's own technique, feasible in weeks) that classifies each task and dispatches it: known recurring type → specialist; novel / low-confidence → escalate to the generalist. **The router's accuracy caps the system, so it is the primary design focus.**
- **Specialist tier (the employees).** One 70B-class open-weight base with **hot-swappable LoRA adapters**, one adapter per recurring task. Fast, cheap, captures fine-tuning *inside* the system.
- **Generalist tier (the senior partner).** Ensemble of 2–3 diverse open-weight models generate candidates; **selection is per-task-type** (the key fix, see §3): an *automated verifier* on verifiable tasks, a *judge* on subjective ones. Reserved for the hard tail.

**Six-week target:** a working prototype, not a product — a routed local system, scored against frontier and a simpler baseline, with an honest per-task picture and a cost model.

**Explicitly out of scope:** broad open-ended frontier parity; the self-training-specialist loop (auto adapter creation); production hardening, security, multi-user serving; any claim of architectural novelty.

---

## 2. Positioning: why this is defensible despite Fugu

Fugu *validates* the architecture and hands us a sharper question. Two competing approaches are built as **explicit baselines** so the result is credible:

- **"Why not call GPT/Claude?"** → data locality + zero marginal cost, and in the export-control regime, *you may not be able to.* The system runs entirely on-prem.
- **"Why not fine-tune one model per task?"** → on a single narrow task it likely wins, and we *use* fine-tuned specialists for those. The architecture earns its complexity only on **breadth** — many task types, including novel ones, in one system. So we must prove **breadth-at-quality**, not single-task quality.
- **"Isn't this just Fugu?"** → Fugu orchestrates *frontier cloud APIs*. We test the *fully-local open-weight* regime Fugu doesn't address, and we measure the gap. That gap is the finding.

**Baselines we build and measure against:** (a) frontier API — the quality bar; (b) single fine-tuned model / fine-tune-and-route — the simplicity bar; (c) ensemble-on-everything — the cost ceiling. If the simpler fine-tune-and-route baseline wins, that is a legitimate, reportable finding.

---

## 3. The fix that makes this rigorous: verifiability-weighted basket + two-mode selection

The previous plan's deep flaw: it moved to consulting tasks that have **no automated ground-truth verifier**, which silently turned the generalist's selector into a judge (a model = a ceiling) and the scoring into a subjective rubric. **Labelability (a human can score it offline) is not verifiability (an automated selector can pick the best candidate at inference time).** We separate the two and weight the basket toward checkable tasks.

**The committed task basket — 3 types, focused:**

| Task | Verifiable? | Inference-time selection | Eval scoring |
|---|---|---|---|
| **Clause/term extraction** from contracts | **Yes** — reference spans | automated: match against reference → pick passing candidate | Exact-match / F1 vs. gold |
| **Grounded document Q&A** over a corpus | **Yes** — checkable vs source | automated: citation-faithfulness / groundedness check | answer-match + faithfulness/citation accuracy |
| **House-style memo drafting** (or summarization) | **No** — subjective | trained judge (best-effort) | **blind human pairwise preference vs frontier** (never LLM-judge declaring parity) |

The two verifiable tasks are the **showcase**: there, generate-and-verify genuinely lets the local ensemble approach frontier, and the claim is defensible by an automated metric. The subjective task is reported **honestly as judge-bounded**, evaluated by blind human preference, not by an LLM judging itself.

Specialist adapters target the two verifiable tasks (where ground truth makes training data and scoring tractable).

---

## 4. Architecture, concretely

- **Router:** train a classification head on a frozen ~7B model's hidden states (task-type + a confidence score). Start with aggressive escalation (low-confidence → generalist). Log every decision for the Week-4 tuning pass. Fugu-style learned routing, not a hand-tuned threshold.
- **Specialists:** 70B-class open-weight base (e.g., Qwen3-72B / Llama-3.3-70B — pick the strongest available at kickoff) + LoRA adapters, one per verifiable task. Served with **multi-LoRA hot-swap** (vLLM / SGLang — both support this).
- **Generalist:** 2–3 *diverse* open-weight models (different families, e.g. Qwen / Llama / DeepSeek-class) for candidate diversity; sample N candidates; **select by automated verifier (verifiable tasks) or judge (subjective)**.
- **Memory discipline (new — borrowed from Fugu to prevent "orchestration collapse"):** explicit **intra-tier isolation** (each tier/agent sees only a designated access list, not the whole history) plus a **persistent shared scratchpad** for multi-step state. Define exactly what each component reads. This is a named failure mode in Fugu; we engineer against it from day one.

---

## 5. Evaluation methodology (per-task-type, defensible)

- **Verifiable tasks:** automated metrics only — extraction (EM/F1 vs. gold spans), grounded Q&A (answer-match + citation-faithfulness/groundedness). This is the ground-truth core.
- **Subjective task:** **blind human pairwise preference** vs. frontier — ≥3 raters, win/tie/loss rate, inter-rater agreement reported. No LLM-as-judge in the headline claim.
- **Cost model:** cost-per-task and cost-per-*solved*-task for routed-system vs. frontier vs. ensemble-on-everything, including amortized GPU + electricity. State honestly that local wins on marginal cost and at volume; frontier may win at low volume.
- **Rules (non-negotiable):** fixed task set across all configs (paired); ≥3 runs where stochastic; report mean ± CI; pin model versions/quants/params; the eval workstream owns the scoreboard.

---

## 6. Team & workstreams (4 people, near-full-time, coding with Claude Code)

| Workstream | Owner | Responsibility |
|---|---|---|
| **Infra & Serving** | A | Baremetal inference (vLLM/SGLang), 70B + multi-LoRA serving, ensemble serving, quantization, GPU scheduling, memory-isolation plumbing |
| **Router & Specialists** | B | Trained router head + confidence/escalation, 2 LoRA adapters for the verifiable tasks, adapter registry |
| **Ensemble & Selection** | C | Multi-model candidate generation, the **automated verifiers** (extraction match, citation/groundedness checker), v0 selector, contingent trained judge |
| **Eval & Benchmark** | D | Benchmark build, frontier + fine-tune-and-route baselines, automated metrics + blind-human-eval protocol, cost model, scoreboard |

Critical path = **router + eval harness** (the two things that determine whether the result can be proven). Adapter training is parallel/off-critical-path.

---

## 7. Compute & the Week-0 hardware gate

**Resolve before Week 1 — the plan's #1 unverified assumption.** The architecture needs substantial concurrent VRAM: a 70B base + multi-LoRA, *plus* a 2–3 model ensemble, *plus* baseline scoring.

- 70B in fp16 ≈ **140 GB** (2× 80 GB); a 3×70B ensemble in fp16 ≈ **~420 GB**.
- **Mitigation — plan for 4-bit/AWQ quantized serving:** 70B ≈ ~40 GB, 3×70B ≈ ~120 GB (fits ~2× 80 GB). Quantization is the lever that makes this feasible.
- **Get the exact GPU count/VRAM in writing in Week 0.** Fallback ladder if limited: (i) quantize harder; (ii) shrink ensemble to 2 models; (iii) drop to 32B-class models; (iv) serve sequentially during scoring windows.
- Adapter fine-tuning (light, parallelizable) → Colab/spare capacity, batch only. All serving + eval → baremetal.

**Data source — resolve in Week 0:** verifiable-task data can use public proxies (public contracts/EDGAR filings for extraction; a public corpus for grounded Q&A) so there is real ground truth. If consulting data is synthetic, say so — then the claim is "on a realistic public proxy," not "on a real firm's confidential work."

---

## 8. Six-week plan (Week 0 + 6, gates in bold)

**Week 0 — De-risk the two killers.** Confirm exact GPU/VRAM. Confirm data sources with real ground truth for the two verifiable tasks. **GATE: hardware allocation in writing + labelable, ground-truth datasets identified — or adjust scope before building.**

**Week 1 — Foundations.** Commit the 3-task basket (2 verifiable + 1 subjective). Build benchmark v0 (15–25 items/task) with gold answers for the verifiable tasks + the blind-eval protocol for the subjective one. Stand up 70B + multi-LoRA hot-swap on baremetal (quantized). Run the **frontier baseline** so there's a number to beat from day one. **GATE: basket committed; benchmark + scoring live; frontier scored; serving with hot-swap demonstrated.**

**Week 2 — Specialists + thin generalist.** Train 2 LoRA adapters for the verifiable tasks (parallel, Colab). Stand up ensemble v0 with the **automated verifier selector** on verifiable tasks + a simple LLM-judge on the subjective one. Domain bake-off: confirm which tasks the local approach can realistically approach frontier on; cut any hopeless task. **GATE: adapters beat base on their tasks; ensemble-v0 runs end-to-end; viable basket confirmed.**

**Week 3 — Routing + first full slice (the critical milestone).** Build router v1 (trained head + escalation). Integrate router→specialist→generalist into one path. Run the full routed system across the basket; score vs. **frontier + fine-tune-and-route**. Measure misroutes. **GATE: end-to-end routed system scored against both baselines. This is the thin-slice gate; everything after is improvement, not new architecture.**

**Week 4 — Improve, don't expand (judge is contingent).** Tune the router from the misroute log (better features, threshold). **If — and only if — Week 3 is on time:** train the judge adapter for the subjective task and re-score; otherwise keep the v0 selector and spend the week reducing misroutes and hardening the verifiers. Re-run the full benchmark; quantify each change's contribution. **GATE: router misroute rate measurably down; full-system numbers improved over Week 3.**

**Week 5 — Hardening, cost, long tail.** Stress on novel/out-of-distribution tasks → confirm graceful escalation. Tune candidate count/budgets for the quality/latency/cost tradeoff. Complete the **cost model** (routed vs frontier vs ensemble-on-everything). Fix worst failure modes; re-label disputed eval items. **GATE: cost curve complete; graceful degradation shown; scores stable across re-runs.**

**Week 6 — Lock & package.** Feature freeze; final clean benchmark run; record every KPI. Results write-up (quality, latency, cost, data-locality) vs. both baselines, positioned as the local-regime extension of Fugu (cited). Live demo path (routing to specialist vs. generalist). Document what worked/didn't + the deferred self-training-specialist loop as headline future work. **GATE: KPIs locked; results doc + demo ready; honest assessment of the gap to frontier.**

---

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **Worker-quality ceiling** (Fugu's lesson): local 70B workers cap the system below frontier | Recalibrated claim — match frontier only on verifiable tasks via generate-and-verify; report the gap on the rest. Never promise parity. |
| **Verification/domain mismatch**: subjective tasks have no automated selector | Basket weighted to verifiable tasks; subjective task is judge-bounded + blind-human-evaluated, reported honestly. |
| **Hardware doesn't fit** | Week-0 GPU gate + quantization + fallback ladder (smaller ensemble / 32B / sequential serving). |
| **Scope blowout** (two training loops) | Judge training is *contingent* on Week-3 being on time; thin measured slice by Week 3; back half is improvement, not architecture. |
| **Orchestration collapse** | Intra-tier memory isolation + shared scratchpad with explicit access lists, from day one. |
| **Router misroutes** | Aggressive escalation default; log + tune in Weeks 3–4; router is the staffed primary focus. |
| **Over-building with Claude Code** | Eval is a first-class staffed workstream; the scoreboard gates every week. |
| **Fine-tune-and-route baseline wins** | Treated as a legitimate, reportable finding — built explicitly. |
| **Data is synthetic** | Use public proxies with real ground truth; if synthetic, state the claim is "on a realistic proxy." |

---

## 10. Definition of done (recalibrated, honest)

The six weeks succeed if, on the committed basket and our benchmark, we can show:

- A **fully-local routed system** (trained router + LoRA specialists + ensemble/verifier generalist) running end-to-end on our hardware.
- **Matches frontier on the verifiable tasks** (extraction, grounded Q&A) by an automated metric; **approaches it on the subjective task** by blind human preference — with the honest per-task picture, never a cherry-picked headline.
- **Lower marginal cost** than ensemble-on-everything, and a clear, honest cost-vs-frontier comparison (incl. the volume crossover).
- A **credible comparison to fine-tune-and-route**, whichever way it falls.
- Positioned and cited as the **fully-local extension of the Fugu/TRINITY orchestration idea** — no novelty claim, a measured-gap claim.

A strong partial result — matching frontier on the verifiable tasks, approaching it on the subjective one, cheaply and privately — is a successful POC. Broad open-ended frontier parity is explicitly **not** the bar, and claiming it would be the fastest way to lose credibility.

---

## 11. What we are explicitly NOT claiming

- Not that cheap local models *are* frontier models (Fugu reached frontier with frontier workers; we won't).
- Not architectural novelty (the pattern is Fugu's / TRINITY's / Conductor's; we cite them).
- Not production-readiness, security, or multi-user serving.
- Not parity on open-ended subjective work.

Stating these up front is what makes the rest believable.
