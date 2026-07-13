# SAIL Chat — Design System

Benchmarked off Mastercard's system discipline (`npx getdesign add mastercard`,
2026-07-13): committed radius scale, weight-450 body, halo shadows, whitespace
as structure. Identity is entirely our own: white canvas, one grey ramp, ink
for action. Register: **product** (tool UI; design serves the task). Personality:
calm, precise, trustworthy.

## 1. Visual Theme

A white instrument panel for watching an AI pipeline work. The canvas is pure
white; structure comes from a single cool-grey ramp used at hairline weight.
Nothing is decorated: every grey line, chip, and card exists to make the
machine's behavior legible. The signature gesture is **quiet geometry** — a
small committed radius scale, shadows so soft they read as air, and generous
space between conversation turns. Event-stream elements (router chip, tool
cards) are set in mono as the "machine voice"; prose answers are set in the
humanist sans as the "human voice". That two-voice contrast is the identity.

**Key characteristics**
- Pure white canvas; cool near-white panel tone for the sidebar only
- Hairline (1px) grey borders; borders and space do the structural work, no boxes-in-boxes
- Two voices: sans for human content, mono for machine events (tool names, args, telemetry)
- Ink-black primary actions (no accent color for buttons)
- Semantic color appears ONLY as status: success / failure / running
- Waiting states are designed, not left blank: shimmer, pulse, progress affordances

## 2. Color Palette & Roles

Strategy: **Restrained** — tinted neutrals + semantic status only. OKLCH throughout.

### Surfaces
- `--bg` `oklch(1 0 0)` — page canvas, pure white
- `--panel` `oklch(0.977 0.002 260)` — sidebar / second neutral layer (≈ #f6f7f8)
- `--raised` `oklch(1 0 0)` — cards/popovers on panel; white lifted by border + halo shadow

### Ink ramp (cool grey, hue 260)
- `--ink` `oklch(0.22 0.01 260)` — headings, body, primary buttons (≈ #1b1d22)
- `--ink-2` `oklch(0.45 0.012 260)` — secondary text, labels (≈ #565b64) — 4.5:1+ on white
- `--ink-3` `oklch(0.58 0.01 260)` — timestamps, placeholder-adjacent metadata only (≥18px or non-essential)
- `--border` `oklch(0.922 0.004 260)` — hairline borders (≈ #e4e5e8)
- `--border-strong` `oklch(0.85 0.006 260)` — input borders, hover borders

### Semantic (status only — never decorative)
- `--ok` `oklch(0.55 0.14 150)` — gate PASS, tool success (muted green)
- `--err` `oklch(0.55 0.19 25)` — errors, gate FAIL (muted red)
- `--run` `--ink-2` — running/working states stay grey; motion carries the signal, not color

Rules: no gradients; no color on inactive states; grey text never sits on a
tinted background (use a deeper step of the ramp instead).

## 3. Typography

- **Sans (human voice)**: Inter (variable), fallback `system-ui`. Body at
  **weight 450** — the Mastercard trick; softer than 500, firmer than 400.
- **Mono (machine voice)**: `ui-monospace, "SF Mono", Menlo, monospace` — tool
  names, arguments, outputs, token/cost telemetry. Always with `font-variant-numeric: tabular-nums` for metrics.
- One family per voice; no display font anywhere.

| Role | Size | Weight | Tracking | Notes |
|---|---|---|---|---|
| Panel/section label | 11px | 550 | +0.04em | sidebar group headers ("Sessions", "Skills"); the ONLY uppercase in the app |
| Body / messages | 15px | 450 | 0 | line-height 1.6; max 72ch |
| Machine text (mono) | 12.5px | 450 | 0 | tool cards, chips, meter |
| Session title / H-ish | 15px | 550 | -0.01em | no big headings in a tool |
| Composer input | 15px | 450 | 0 | matches body |

Fixed rem scale (product register) — no clamp/fluid type.

## 4. Shape, Depth & Motion

### Radius scale (committed; nothing in between)
- `6px` — chips, badges, small controls
- `10px` — buttons, inputs, tool cards, message bubbles
- `16px` — floating panels, popovers, composer surface
- `999px` — status dots and avatar circles only

### Elevation (halo philosophy: huge spread, ≤8% opacity, never hard)
- Level 0 — none; 95% of the UI sits flat on white
- Level 1 — `0 4px 24px rgba(0,0,0,0.04)` — composer surface, active popover
- Level 2 — `0 24px 48px rgba(0,0,0,0.07)` — modals only
- Prefer hairline borders over shadows for delineation.

### Motion
- 150–250ms, `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out-quint feel); state changes only
- Working states: pulsing dot / shimmer on the pending turn; tool card border
  breathes while running — motion signals state, color does not
- No page-load choreography; no bounce
- Every animation has a `prefers-reduced-motion` fallback (static "Working…" text / opacity swap)

## 5. Components

**Buttons** — Primary: ink bg, white text, 10px radius, 8px×16px padding,
weight 500. Secondary: white bg, `--border-strong` hairline, ink text. States:
hover darkens/tints one step, focus = 2px ring `--ink` offset 2px, disabled =
40% opacity. One shape everywhere.

**Router chip** — mono 12.5px, 6px radius, hairline border, `--ink-2` text,
white bg. Reads `coding · 0.75 · worker`. Not a pill, not colored.

**Tool card** — 10px radius, hairline border, white bg. Header row: mono tool
name (ink) + status affordance right-aligned (running = pulsing grey dot,
done = small `--ok` check, failed = `--err` ×). Body (expanded): panel-tone
inset with mono args/output, max-height scroll. Border animates subtly while
running.

**Messages** — User: right-aligned, panel-tone bubble, 10px radius, max 60%
width. Assistant: no bubble — flat on canvas, full measure (72ch); the
machine-event cards above it provide the structure.

**Composer** — Level-1 floating surface, 16px radius, hairline border;
textarea borderless inside; send button = primary ink. Model picker + [+] as
quiet secondary controls in the same surface.

**Sidebar** — `--panel` bg, hairline right border. Group labels per typography
table. Rows: 6px radius hover tint, active row = white bg + hairline border.
Pin star only on hover/active. Width 240px, collapses under 900px.

**Context meter** — mono, tabular numbers, `--ink-3`, bottom-right. Ticks up
live; brief opacity pulse on update.

**States** — every interactive element ships default / hover / focus / active /
disabled; loading uses skeletons or designed working-states, not spinners;
empty session list teaches ("Start a session — your history lives here").

## 6. Layout

- Base unit 4px; spacing steps 4 / 8 / 12 / 16 / 24 / 32 / 48
- Chat column max-width 760px centered in the content pane
- Turn-to-turn gap 32px; event-to-event gap inside a turn 8px — conversation
  rhythm comes from space, not dividers
- Sidebar 240px fixed; content pane fluid; meter pinned bottom-right
- Structural responsiveness (collapse sidebar), not fluid type

## 7. Do / Don't

**Do**: hairline borders; mono for everything the machine says; designed
waiting states; tabular numerals for cost; whitespace as hierarchy; one focus
ring style everywhere.

**Don't**: colored accents on chrome; pills; gradients; glassmorphism; cards
inside cards; uppercase outside the 11px panel labels; muted grey below 4.5:1
for essential text; spinners centered in content; decorative motion.
