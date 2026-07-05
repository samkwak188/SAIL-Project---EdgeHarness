# Skill: knowledge-task

Execute a knowledge-work task: extraction, grounded Q&A, or memo drafting.

## When to use
Task is over a document corpus (contracts, filings, memos).

## Procedure by subtype

### Extraction (verifiable)
1. Orchestrator routes to `specialist` with extraction LoRA if available, else generalist
2. WorkflowPlan.gate = JSON schema validation against expected span structure
3. Worker reads the source doc + schema; emits structured JSON to scratchpad:task.artifacts
4. Verifier validates JSON against schema (deterministic) — PASS → Done

### Grounded Q&A (verifiable)
1. Orchestrator routes to `specialist` (qa_lora) or generalist
2. Worker retrieves via memory_search with the user's allowlist (tenant/ACL/time)
3. Worker emits answer with inline citations [doc_id, span]
4. WorkflowPlan.gate = citation-faithfulness script (each citation must appear in allowlisted docs)
5. Verifier runs the script — PASS → Done

### Memo drafting (subjective)
1. Orchestrator routes to `generalist` ensemble (2–3 candidates)
2. Verifier acts as judge with rubric (relevance, accuracy, currency, hallucination, 1–5)
3. Note: judge-bounded — reported honestly, never as parity in the headline claim
4. Blind human pairwise preference is the headline metric for this subtype (v2 plan §5)

## Never
- Worker fabricates a citation not present in the allowlisted corpus
- Verifier judges its own maker session
