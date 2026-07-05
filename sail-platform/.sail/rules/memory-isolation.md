# Rule: memory isolation

Each agent sees only its access list — never the full chat history.

## Access lists (defaults; orchestrator may narrow per task)

| Role | May read | May write |
|------|----------|-----------|
| orchestrator | vision, state, scratchpad:meta, scratchpad:plan | scratchpad:meta, scratchpad:plan |
| planner | vision, scratchpad:task, scratchpad:plan | scratchpad:plan |
| worker | scratchpad:task (own step only), retrieval:scoped (allowlisted), assigned files | scratchpad:task/<step-id>/, artifacts |
| verifier | scratchpad:task, artifacts, gate_output, gate definition from WorkflowPlan | state (Done/Blocked only), scratchpad:verdict |
| researcher | vision, scratchpad:research, research/, memory_search | research/, scratchpad:domain_candidates |

## Enforcement
- The harness `context.py` assembler filters the scratchpad by access list before injecting
- `spawn_agent` passes only the access_list slice to the child context
- The worker's access list MUST NOT include the gate definition (gate authored by orchestrator)
- Violations are telemetry-logged as `isolation_violation` and abort the step

## Rationale
Fugu's "orchestration collapse" failure mode: when every agent sees the whole history,
errors compound and tier boundaries dissolve. Intra-tier isolation is the engineering fix.
