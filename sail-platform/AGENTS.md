# AGENTS.md — sail-platform

**Read [ARCHITECTURE.md](ARCHITECTURE.md) first.** It maps the control flow, every
component, and where to add new task types / tools / agents / providers.

## Mental model

The Python is the **engine**; `.sail/` is the **behavior**. Agent personas, rules,
routing, and constraints live in `.sail/*.md` and `config/*.yaml` — not hardcoded in
Python. Put new behavior in config unless it genuinely needs code.

## Before you edit — three gotchas

1. **Stub mode hides bugs.** `config/models.dev.yaml` never round-trips real tool
   calls. Test any provider/tool-call change against a live model
   (`config/models.openrouter.yaml`, needs `OPENROUTER_API_KEY` in `.env`), not just stub.
2. **Task runs dirty the git tree.** They edit `examples/fixtures/smoke_coding.py` and
   `.sail/STATE.md`. Run `git checkout -- examples/fixtures/smoke_coding.py .sail/STATE.md`
   afterward.
3. **`litellm[proxy]` is required** for tool calling — plain `litellm` errors mid-call.

## Verify your changes

Run the coding smoke task end-to-end against a real model and confirm `verdict: PASS`:

```bash
source .venv/bin/activate
set -a && source .env && set +a
python cli.py task run examples/smoke_coding.yaml --config config/models.openrouter.yaml
```

## Commits

No `Co-Authored-By` trailer. Short subject line, details in the body.
