# Skill: coding-task

Execute a SWE-style coding task through the harness loop.

## When to use
Task is a code change in a repo with executable tests.

## Procedure
1. Orchestrator routes to `worker` (path: specialist if a coding LoRA exists, else generalist/worker)
2. WorkflowPlan.gate = the repo's test command (e.g. `pytest -q <test_path>`)
3. Worker:
   - read failing test + targeted source files (no full repo dump — use grep/glob + memory_search)
   - make the smallest change that fixes the failing test
   - do NOT run the gate (verifier does that)
4. Verifier runs the gate in sandbox; PASS → Done; FAIL → escalation ladder
5. Telemetry records tokens, latency, retry rung, gate result

## Edit-format default
str_replace with read-before-edit (settings.harness.edit_mode).
Fallback: whole_file write on repeated str_replace failure.

## Never
- Worker authors or modifies the gate command
- Worker runs tests directly (would self-grade)
- Edit a file without reading it first in the same session
