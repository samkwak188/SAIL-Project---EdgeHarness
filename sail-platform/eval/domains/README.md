# Eval domains — populate after the domain bake-off

This directory is intentionally empty until the domain-bakeoff skill produces
`basket.yaml` (the committed task basket of 2 verifiable + 1 subjective task
types per v2 plan §3).

Activation checklist (run `sail eval readiness-check` to verify):
- [ ] domain_decision_record.md written
- [ ] basket.yaml committed with >= 3 task types
- [ ] 15-25 items per task type with gold labels (verifiable tasks)
- [ ] blind human pairwise protocol defined (subjective task)
- [ ] frontier API baseline scored
- [ ] fine-tune-and-route baseline scored
- [ ] ensemble-on-everything baseline scored
- [ ] cost model fields defined ($/task, tokens/solved, GPU hours)

Until then, the eval harness raises NotImplementedError on run/compare.
