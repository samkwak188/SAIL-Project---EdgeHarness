# Skill: domain-bakeoff

Research + outreach to pick eval domain BEFORE activating eval harness.

## Phase A — Research (automated)
1. researcher agent surveys: consulting pain points, verifiability, data availability
2. Score candidates on: {automated_verifier_possible, local_model_feasible, outreach_interest, data_access}
3. Write report to scratchpad:domain_candidates

## Phase B — Outreach (human-in-loop)
1. Generate outreach templates for top 3 candidates
2. HUMAN sends outreach; HUMAN records responses in scratchpad:outreach_log
3. Re-score with outreach signal

## Phase C — Commit basket
1. Orchestrator proposes final 2 verifiable + 1 subjective task types (v2 plan pattern)
2. HUMAN approves → write config/eval/domains/basket.yaml
3. Run `sail eval init` to scaffold harness

## Output artifact
domain_decision_record.md: chosen domain, rejected alternatives, evidence, eval plan
