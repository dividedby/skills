# Direction Doc Format

The contract for `docs/design/direction.md` — the living current-state
document `/frontend-design` reads or creates in **Bootstrap** (Step 1 of
the Iteration Loop). This file is the `/frontend-design` analog of `/software-design`'s TDD-ready
issue format: it defines the shape of the artifact the skill writes, not the
artifact itself.

`docs/design/direction.md` is the single source of truth for the committed
aesthetic direction. Step 5 (Design Language Instantiation) reads from it
to write `tokens.css`; the stamping pass in `/software-design`
mechanically pastes its path into frontend-flavored issue bodies. The
direction doc never inlines token values — it names *intent*; tokens live
at the *Token authority path*.

---

## The 9-Field Spec (+1 optional)

In document order:

1. **Name** — 1–3 evocative words. E.g. *Editorial Mono*, *Tactile Brutalism*, *Warm Telemetry*.
2. **One-paragraph description** — the visual feel in prose; what the user sees and how it makes them feel.
3. **Typography intent** — voice (editorial / utilitarian / expressive / display-led) and a constraint (serif-leaning, mono-accents, variable-only, no Inter/Roboto, etc.). Maps to type roles + font choices that Step 5 instantiates.
4. **Palette intent** — temperature/mood and saturation posture (muted / saturated / monochrome+accent). Maps to color tokens (see [design-tokens.md](design-tokens.md)) that Step 5 instantiates.
5. **Layout personality** — density (airy / dense / editorial-column / dashboard-grid) and rhythm posture (uniform / varied). Maps to grid, spacing, and depth tokens.
6. **Motion character** — speed (snappy / considered / still) and spring posture (springy / damped / no-spring). Maps to duration / easing / spring policy.
7. **Anti-direction** — what this direction is **NOT**, in ≥2 named contrasts. Forces the positive direction to be sharp by naming what it rejects.
8. **Banned-pattern overrides** — explicit per-row acknowledgements that unlock specific BLOCK-tier entries from `banned-patterns.md`. Each override gives a one-line brand-specific reason. Resolved once here, never re-grilled per component.
9. **Token authority path** — relative path inside the repo where the instantiated `tokens.css` (or Tailwind theme block) lives. The file need not exist at bootstrap time; Step 5 creates it.
10. **References** *(optional)* — links to inspirations, screenshots, brand assets. Pure context; never read mechanically.

---

## Grilling Order

The skill grills fields in this order during Bootstrap — **not** document
order. Description first to anchor the positive vision; Anti-direction
second to immediately sharpen it; the four lenses (type/palette/layout/
motion) next; Name late so it summarises a formed direction rather than
imposing one; mechanical fields last.

| # | Field |
|---|---|
| 1 | One-paragraph description |
| 2 | Anti-direction |
| 3 | Typography intent |
| 4 | Palette intent |
| 5 | Layout personality |
| 6 | Motion character |
| 7 | Name |
| 8 | Banned-pattern overrides |
| 9 | Token authority path (+ optional References) |

### Anti-direction at position #2

Grilled right after the description, before the four lenses: naming what
the direction rejects while the description is fresh constrains the
lenses from the first stroke, instead of retrofitting contrast once
they've already drifted into generalities.

### Cap: 2 attempts per field

For each field, the skill grills at most **2 times**. On the **3rd
attempt** the skill accepts whatever the user has said and writes the
value with a literal `Tentative:` prefix. Tentative fields are honoured by
Step 5 (which falls back to conservative defaults) and flagged in the
Step 7 audit so the user can revisit.

---

## "Good Enough to Commit" Bars

Each field passes when it meets its bar. Below the bar, the skill grills
again (subject to the 2-attempt cap).

| Field | Bar |
|---|---|
| Description | ≥3 sentences **or** ≥2 concrete reference points (named site, product, era, or medium) |
| Anti-direction | ≥2 named contrasts — not "not bad design", "not generic", or other empty negatives |
| Typography intent | Voice (editorial / utilitarian / expressive / etc.) **and** a constraint (serif-leaning, mono-accents, variable-only, …) |
| Palette intent | Temperature/mood **and** saturation posture (muted / saturated / monochrome+accent) |
| Layout personality | Density (airy / dense / editorial-column / dashboard-grid) **and** rhythm posture (uniform / varied) |
| Motion character | Speed (snappy / considered / still) **and** spring posture (springy / damped / no-spring) |
| Name | 1–3 words, evocative; reject "Modern", "Clean", "Minimal", "Sleek" |
| Overrides | Either empty (default) **or** an explicit list with one-line reason per entry |
| Token authority path | Valid relative repo path; the file itself need not exist yet |

---

## Refusal Handling

Bootstrap is interactive; some users will resist it. Three refusal modes:

### Soft refusal — "just pick something"

The skill generates 2–3 directions itself, picks the most defensible for
the stated stack and intent, and writes `docs/design/direction.md` with
the literal annotation `Proposed-by: skill` on each field. The user may
edit later. The paired ADR (see below) notes *"direction proposed by
skill, accepted without modification."*

### Hard refusal — "I don't want a direction"

**BLOCK.** The skill surfaces the off-ramp:

> This skill requires a committed direction. If you want to skip the
> direction step, use `/tdd` directly with a styling pass — the result
> will not be design-reviewed by `/frontend-design`.

No direction doc is written. No ADR is written.

### Partial refusal — pushback on specific fields

For each resisted field, after the 2-attempt cap, the skill writes
`Tentative:` prefix on that field (per *Good Enough to Commit*). Step 5
instantiates **conservative defaults** for tentative fields (system font
stack, neutral palette, standard durations) and flags every tentative
field in the Step 7 audit. The paired ADR lists which fields are
tentative.

---

## ADR Pairing Rule

Bootstrap is a two-artifact write. In a single pass, `/frontend-design`
creates:

1. `docs/design/direction.md` — the 9-field direction doc (living document).
2. `docs/adr/NNNN-frontend-design-direction.md` — an ADR recording the decision (immutable record).

Both files are written together. Neither is deferred to a follow-up skill.
The ADR follows the shape defined in
the installed `/grill-with-docs` skill's `ADR-FORMAT.md` (the
project's canonical ADR template) — the *Decision* section is the chosen
direction; the *Consequences* section captures which `banned-patterns.md`
rows are unlocked and any tentative fields.

**Token values are not ADR-worthy.** Specific font sizes, OKLCH values,
duration milliseconds, etc. live in `tokens.css` at the Token authority
path. They change without an ADR. Only the *direction* — the intent the
tokens express — is recorded as a decision.

### Deliberate departure from `/software-design`

`/software-design` defers all ADR writing to `/grill-with-docs` (see its
"Surface durable items for extraction" step). `/frontend-design`
intentionally does **not** defer: it writes both artifacts in the
bootstrap pass.

Why: the direction is a one-shot decision that gates every subsequent
component, and the user is already in a design conversation. Bouncing the
user out to `/grill-with-docs` mid-bootstrap fragments the session and
risks the ADR never being written. The trade-off is accepted; do not
"correct" this back to the deferral pattern.

---

## Example: A Filled-in Direction Doc

```markdown
# Direction: Warm Telemetry

> Status: committed · Created: 2026-03-12 · ADR: docs/adr/0007-frontend-design-direction.md

## Name
Warm Telemetry

## Description
Reads like a well-printed instrument panel, not a generic SaaS app: warm
near-black surfaces, numbers carrying weight, chrome receding for data.
References: Bloomberg Terminal, Tufte's *Envisioning Information*,
1985-era Honeywell control rooms.

## Anti-direction
- **Not** cyberpunk-dashboard (no neon, no glow, no monospace-as-aesthetic).
- **Not** SaaS-marketing (no gradient hero, no glassmorphism, no
  eyebrow-h2-paragraph rhythm).

## Typography intent
Utilitarian-editorial, tabular-numeric. Sans display (Söhne Breit) for
headings, humanist sans (Inter Tight, brand-justified) for body,
tabular-mono (Berkeley Mono) for table/chart numbers.

## Palette intent
Warm and muted, monochrome plus one earned accent. Near-black base tuned
toward umber; desaturated amber for active/positive, rust for negative.
No saturated hues outside data.

## Layout personality
Dense, editorial-column, varied rhythm. 12-column desktop grid,
single-column mobile with horizontal-scroll tables. No bento.

## Motion character
Considered and damped, no springs. 120–200ms, ease-out enter / ease-in
exit. Charts animate in once, never on filter change.

## Banned-pattern overrides
*(none)*

## Token authority path
`app/styles/tokens.css`

## References
- Honeywell TDC 3000 console photographs
- Tufte, *Envisioning Information* (1990), ch. 2
```
