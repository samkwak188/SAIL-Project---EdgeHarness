# SAIL Local AI — System Vision

## Mission
Run knowledge-work and coding tasks fully on-prem with orchestrated multi-agent loops.
No confidential data leaves our network.

## Current phase
ARCHITECTURE + DOMAIN RESEARCH. Eval harness activates after domain bake-off.

## Stop condition (verifiable)
- `sail eval readiness-check` exits 0 when: orchestrator E2E demo passes AND domain basket committed.

## Hard stops (never violate)
- Never merge, deploy, or send external network requests with user data without explicit approval.
- Never weaken a verification gate to force progress.
- Never edit VISION.md during a loop cycle.
- Checker agent is the only role allowed to mark items Done in STATE.md.

## Scope boundaries
- In scope: router, harness loop, turbovec memory, hybrid model pool, research/outreach.
- Out of scope until domain pick: domain-specific benchmark items, LoRA training, production multi-tenant serving.

## Quality gates
| Gate | Command | Pass criteria |
|------|---------|---------------|
| Unit loop | `sail loop --once --dry-run` | Completes one cycle, STATE updated |
| Orchestrator E2E | `sail task run examples/smoke_coding.yaml` | Worker executes, Checker verifies |
| Memory | `sail memory search "test" -k 5` | turbovec returns results < 500ms on dev corpus |

## Architecture references
- `PROJECT_PLAN_v2_local-orchestration.md` (root) — supersedes `Project_Plan_Jack.pdf`
- `HARNESS_INTERNALS_REFERENCE.md`, `HARNESS_RESEARCH_GUIDE.md` (root)
- Plan file: `.cursor/plans/local_ai_orchestrator_6e0c061d.plan.md`

## Honest positioning
Orchestration rides on worker quality; local open-weight workers cap the ceiling below frontier.
Claim is a **measured gap**, not parity. The eval harness proves the gap per domain later.
