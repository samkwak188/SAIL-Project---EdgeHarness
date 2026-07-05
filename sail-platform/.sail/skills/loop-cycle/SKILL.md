# Skill: loop-cycle

Run one autonomous loop iteration.

## Trigger
/sail loop --once OR scheduled OR stop-hook

## Steps
1. Read `.sail/VISION.md`
2. Read `.sail/STATE.md` — pick highest-priority Open item (or discover new work if empty)
3. Spawn orchestrator → get WorkflowPlan
4. If plan.path == parallel: spawn workers in worktrees; else sequential
5. Worker executes ONE unit
6. Spawn verifier (fresh context, different model_role if available)
7. Verifier runs gate; updates STATE
8. Append dated lesson to STATE ## Lessons
9. Check stop condition; exit or continue

## Never
- Skip verifier
- Edit VISION.md
- Run gate from worker session
