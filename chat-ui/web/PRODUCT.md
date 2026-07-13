# Product

## Register

product

## Users

Two audiences share one surface. Day to day: the SAIL team (engineers) driving a
local LLM harness — sending tasks, watching the router/worker/tool pipeline
execute, tracking token cost. Decisive moment: law-firm stakeholders (the DeWitt
pilot) watching a live demo, judging whether this system is trustworthy enough
to touch client work. The user is always mid-task; between events the model can
be silent for 5–40 seconds, so the interface must carry confidence through
waiting.

## Product Purpose

A localhost chat interface over the sail-platform harness. It makes the
invisible pipeline legible: which specialist got the task (router chip), what
the agent actually did (tool cards), what it cost (context meter). Success =
an engineer trusts it enough to live in it, and a lawyer watching a demo reads
it as a serious professional instrument, not a toy.

## Brand Personality

Calm, precise, trustworthy. The tool disappears into the task; nothing decorative,
nothing loud. Quiet confidence — the register of a well-set legal brief, not a
consumer app.

## Anti-references

- **Claude / ChatGPT / Gemini clones** — no borrowed identity from the big chat apps.
- **Hermes Agent's look** — we benchmarked its layout skeleton only; its dark
  gamer-adjacent styling is explicitly not ours.
- **Generic SaaS dashboard slop** — gradient accents, glassmorphism, hero metrics,
  identical card grids.
- **Consumer-soft pill UI** — Mastercard's editorial DNA informs our discipline
  (committed radius scale, halo shadows, weight-450 body), not its bubbly shapes.

## Design Principles

1. **Legibility of the machine** — router decisions, tool calls, and cost are
   first-class UI, rendered the instant they happen. Transparency is the feature.
2. **Never look dead** — every waiting state is an explicit, designed state.
   Perceived liveness is a hard requirement, not polish.
3. **Earned familiarity** — standard affordances, consistent component vocabulary;
   a Linear/Stripe-fluent user should trust it at first sight.
4. **Whitespace as structure** — hierarchy from space and type scale, not boxes
   and dividers. Grey is structural, never decorative.
5. **One quiet voice** — a single type family, a single grey ramp, ink for action,
   semantic color reserved exclusively for status (pass/fail/error).

## Accessibility & Inclusion

WCAG AA. Body text ≥4.5:1 (the main risk in a grey-on-white palette — muted
greys must stay on the ink side), visible focus rings on all interactive
elements, `prefers-reduced-motion` alternatives for every animation, 40px+
touch targets.
