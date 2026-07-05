# Rule: escalation

When to escalate a task or step to a higher tier / different path.

## Triggers
1. Router confidence < 0.75 → escalate to generalist_ensemble (don't guess)
2. Specialist LoRA missing for a known task type → generalist
3. Worker edit fails twice (rung 1 + rung 2 of error-recovery ladder) → tier escalate (smol → default → slow)
4. Verifier gate fails after max_retries → Blocked (do NOT silently retry past max)
5. Novel / out-of-distribution task detected (embedding similarity to nearest exemplar < 0.5) → generalist
6. Subjective output with no deterministic gate → judge (different model_role from maker)

## Error-recovery ladder (per step, bounded by max_retries_per_step)
1. Error-guided retry — feed verbatim error back to same agent
2. Format fallback — switch edit format (str_replace → whole_file)
3. Tier escalation — re-run step on next model rung (smol → default → slow/ensemble)
4. Block + report — move to Blocked in STATE with full failure trail

## Never
- Weaken a gate to force progress
- Retry past max_retries_per_step without escalating
- Skip a rung (jumping straight to Block wastes the cheaper rungs)
- Allow the maker to self-escalate by editing the gate

## Logging
Every escalation event is telemetry-logged with: trigger, from-tier, to-tier, rung, task_id, step_id.
This data feeds both router-v1 training and the cost model.
