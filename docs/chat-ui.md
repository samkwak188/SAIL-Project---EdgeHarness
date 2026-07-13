# chat-ui — plan

A localhost chat interface on top of the sail-platform harness. Doubles as the
client-facing demo (DeWitt pilot). Benchmarked off Hermes Agent's UX skeleton
(sidebar + sessions + model picker), restyled to our own identity.

Decision record (2026-07-12): stack researched (Opus subagent, OSS survey) and
locked with Sunny — build thin custom; do NOT fork Open WebUI / LibreChat /
LobeChat (they assume plain-text + standard function-call rendering; our whole
point is custom events, and two of them have branding-restricted licenses).
Also inspected NousResearch/hermes-agent (MIT, React19+Vite+Tailwind — validates
our stack) and chose not to copy its `web/`: its chat components depend on the
`@nous-research/ui` design system + custom fonts (the exact identity we're
avoiding), it's WebSocket + a large bespoke REST surface, and 90% of its scope
(profiles, channels, cron, plugins, i18n) is out of ours. Reference for IA only.

## Stack

- **Backend** — FastAPI (already in the platform venv) + **SSE**.
  `chat-ui/server/`. Wraps `_build_platform()`; one stream endpoint per message.
- **Frontend** — React + Vite + Tailwind + **assistant-ui headless primitives**
  (MIT) via `useExternalStoreRuntime`. `chat-ui/web/`. assistant-ui gives chat
  mechanics (streaming list, autoscroll, a11y) unstyled; every visual is ours.
- **Event schema** — AG-UI-shaped vocabulary (steal the schema, skip the
  framework): `router_decision`, `tool_call_start`, `tool_result`, `answer`,
  `usage`, `error`.

## Perceived liveness (hard requirement)

A Gemma worker turn takes 5–40s. The chat must never look dead between events:
- Every SSE event renders the instant it arrives (chip appears when routed,
  tool card appears at `tool_call_start`, fills in at `tool_result`).
- Between events, show an explicit working state (animated thinking indicator
  on the pending turn; tool card in "running" state after start, before result).
- If litellm `stream=True` is trivial to pass through the bridge, stream the
  final answer token-by-token; otherwise event-granularity is acceptable for v1
  and token streaming is v2. The working-state indicators are NOT optional.

## Harness touchpoint (the only backend change)

`harness/loop.py::HarnessLoop.run()` gains an optional `on_event` callback,
called per turn / per tool call. Non-breaking; CLI path ignores it.

## V1 scope

- Chat depth: **router + worker loop** per message. Router chip
  (`coding · conf 1.0 · worker`), collapsible tool-call cards (name, args,
  output), answer bubble. No verifier gate in free chat (gates need a task
  definition; task-mode toggle is v2).
- Sidebar: New session · Skills (read-only from `.sail/skills/`) · Pinned ·
  Sessions. Persisted as JSON in `chat-ui/sessions/` (gitignored).
- Composer: model picker reading `config/models.*.yaml` (Gemma 4 today).
  **+ add model**: paste API key → provider auto-detected by prefix
  (`sk-or-`→OpenRouter, `sk-ant-`→Anthropic, `AIza`→Google) → 1-token verify
  ping → append to `.env` + models yaml.
- Bottom-right: context meter — session tokens + running $ (telemetry already
  records both).
- Out of scope v1: Discord/cron surfaces, auth/multi-user, artifacts pane,
  token-by-token streaming (v1 streams at event granularity), task-mode gate
  runs.

## Design

Minimal white with grey accents — own identity, not a Claude/Hermes clone.
Whitespace-driven, a single grey ramp, one restrained signal color reserved
for status (e.g. gate PASS/FAIL when task mode lands). Serif/display flourishes
only if they survive the minimalism bar.

## Build order

1. Backend: `on_event` hook in loop.py + FastAPI SSE bridge + session store
2. Unstyled-but-working chat against live Gemma (prove the stream end-to-end)
3. Design pass (white/grey system)
4. Model picker + add-key flow
5. Sidebar: sessions / pinned / skills

## Run (dev)

```bash
# backend (from sail-platform/, venv active, .env loaded)
uvicorn chat-ui.server.app:app --reload --port 8800   # adjust module path to actual layout
# frontend
cd chat-ui/web && npm run dev                          # vite proxies /api → :8800
```

Verify end-to-end: send "fix the failing test in examples/fixtures/smoke_coding.py
so add(2,3) returns 5" in the UI → router chip `coding`, read+edit tool cards,
answer bubble, ctx meter ticks up. Then reset:
`git checkout -- examples/fixtures/smoke_coding.py .sail/STATE.md`.

## Layout sketch

```
┌───────────┬──────────────────────────────────┐
│ + New     │  [router chip: coding · 1.0]     │
│ Skills    │  ▸ tool: read   (collapsible)    │
│ ─ Pinned  │  ▸ tool: edit                    │
│ ─ Sessions│  answer bubble                   │
│           ├──────────────────────────────────┤
│           │ [composer…]      [gemma-4 ▾][+]  │
└───────────┴──────────── ctx: 4.2k tok · $0.006 ┘
```
