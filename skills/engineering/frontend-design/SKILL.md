---
name: frontend-design
disable-model-invocation: true
description: >
  Design and refine production-grade, opinionated frontend interfaces that
  avoid generic AI aesthetics. Use when asked to "design a UI", "build a
  component", "re-theme this page", "run a design review", or "audit my
  frontend for accessibility".
---

# Frontend Design

A 7-step loop: prose direction → committed `docs/design/direction.md` + paired
ADR → `tokens.css` → components → audited output. Works across React, Next.js,
Tailwind, and vanilla HTML/CSS/JS.

Supporting files (loaded per step, not upfront):
[banned-patterns.md](banned-patterns.md) — tiered anti-pattern catalogue with paired alternatives;
[direction-doc-format.md](direction-doc-format.md) — 9-field spec, bootstrap mechanics, ADR pairing;
[design-tokens.md](design-tokens.md) — color / type / motion / spacing+depth taxonomy.

## Scope

**Use for:** greenfield UIs, re-themes, design reviews, accessibility
audits, design-token foundations, component generation.

**Defaults:** WCAG 2.2 AA minimum, keyboard + screen-reader paths,
`prefers-reduced-motion` respected, fluid from 320 px up, Next.js RSC-safe
unless interactivity is needed.

**Skip for:** pure logic / data-layer, CLI, prose, structural refactors
with no visible change.

**Existing codebases:** read current tokens and components before proposing;
never silently overwrite, but **challenge inherited tokens, stack, or
aesthetic** when they predate this skill and conflict with the brief. Name
the mismatch, propose the better fit, let the user accept or override.

## Inputs

Collect before proceeding — ask, never invent: **Stack**, **Intent**,
**Brand**, **Content structure**, **Constraints**, **Aesthetic direction**.
"Surprise me" on direction → Bootstrap with soft-refusal handling.

## Iteration Loop

### 1. Bootstrap

Check `docs/design/direction.md`. If present and complete (all 9 fields,
paired ADR exists), reuse. If present but **thin, vague, or predates this
skill** (missing fields, no paired ADR, prose-only aesthetic hand-waves),
treat it as a *candidate to challenge* — carry it into Step 2 as one option
alongside a revised proposal, not as a settled default. If missing, grill
the 9 fields per [direction-doc-format.md](direction-doc-format.md) —
ordering, "good enough" bars, 2-attempt cap, `Tentative:` prefix,
soft/hard/partial refusal handling. On completion, write **both**
`docs/design/direction.md` and `docs/adr/NNNN-frontend-design-direction.md`
in one pass.

### 2. Direction Proposal

Greenfield: propose **2–3 named directions**, each with name, one-paragraph
feel, four lens fields (typography / palette / layout / motion),
anti-direction. Otherwise: reuse committed.

### 3. Self-Critique

7-item tiered checklist per proposed direction; evidence required per item:
(1) No BLOCK patterns ([banned-patterns.md](banned-patterns.md)) — bare check or one-line justification per occurrence;
(2) WARN patterns audited — bare check if zero, else one-line reason each;
(3) Clear POV — one-sentence statement;
(4) Distinct from siblings — one phrase per contrast;
(5) Holds shape at 320 / 768 / 1280 — one phrase per breakpoint describing reflow;
(6) Type / color / motion named (no "TBD") — named values in body;
(7) Anti-direction acknowledged — the field itself is the evidence.

**Failure protocol.** BLOCK → silent re-run Step 2 for that slot, cap 2;
on the 3rd surface to user. WARN → annotate, surface in Step 4.

### 4. Confirmation

Present surviving proposals. User picks. Confirm: "Proceeding with
**[Name]**."

### 5. Design Language Instantiation

Write the complete `tokens.css` (or Tailwind theme) at the *Token
authority path* from the direction doc. Direction may not remain prose —
type, color, spacing, depth, and motion all become machine-readable
tokens. Full taxonomy (OKLCH, `light-dark()`, scales): [design-tokens.md](design-tokens.md).

### 6. Generation

Components reference only tokens from Step 5 — no raw values (see
[design-tokens.md](design-tokens.md)).

### 7. Post-Generation Audit

Always runs. **Always-tier (grep):** hex/`rgb(`/named colors outside
`tokens.css`; missing `color-scheme`; missing no-flash script when
toggle exists; raw px in components; ad-hoc `box-shadow`; slop-font
tripwire. **Smoke-tier (Storybook / Playwright / dev server):** render
both modes, axe-core per-mode contrast, toggle visible in both.
**Review Mode tier (opt-in):** dual-mode visual diff, toggle persistence
round-trip, broken focus-ring per mode. Auto-apply unambiguous
always-tier fixes; report the rest.

## Named Direction Rule

Direction commitment is mandatory. Conflicts surfaced explicitly ("that
gradient glow clashes with the editorial-print direction"). Override
only on explicit acknowledgement with a brand-specific reason added to
the direction doc's *Banned-pattern overrides*.

**Slop-font tripwire:** `Inter`, `Geist`, `Roboto`, `Arial` are
default-detection triggers — state the direction-derived justification
*before* emitting one.

## Warning Format

Tiered behavior defined in [banned-patterns.md](banned-patterns.md). Emit
warnings in this format:

```
⚠️  [pattern] ([tier]) conflicts with the "[direction]" direction.
    Instead reach for: [alternative].
    To override, add a brand-specific reason to docs/design/direction.md.
```

## Responsive (HARD RULE)

Audit breakpoints **320 / 768 / 1280**; design considerations 640 / 1024.
**Absolute:** no horizontal scroll at any width ≥ 320 px. Fully
responsive iff **all 7** hold: (1) no horizontal scroll ≥ 320 px;
(2) tap targets ≥ 44×44 px on mobile (WCAG 2.5.5); (3) text readable
(≥ 14 px body; 45–75 ch; sub-45 ch only when intentional); (4) no
content hidden without an equivalent alternative; (5) interactive
affordances reachable at every breakpoint (no hover-only on touch);
(6) layout **reflows**, not just rescales, at 768 and 1280;
(7) images/media use intrinsic sizing (`aspect-ratio`, `object-fit`).
**Query default:** `@container` for component-internal behaviour;
`@media` reserved for page-level shifts (nav, sidebar, route grids).

**Banned failure modes (audited):** horizontal scroll < 360 px; content
hidden on mobile with no alternative; hover-only on touch; fixed-pixel
layouts that scale without reflowing; tap targets < 44×44 px on mobile;
body text < 14 px; modals overflowing viewport without scroll; `100vh`
without `dvh`/`svh` fallback.

## Light / Dark (HARD RULE)

Mechanism by chrome. **Static / marketing / single-screen / embeds:**
`prefers-color-scheme` only; toggle optional. **Apps with persistent
chrome:** three-state toggle **required** — `system` / `light` / `dark`,
default `system`, persist in `localStorage`, respect
`prefers-color-scheme` changes while in `system` mode. Toggle location
priority: header end-cap → settings/profile menu → footer last resort.

**No-flash mandate.** Inline `<head>` script sets the theme class before
first paint. Flash on load is a defect.

**Audit detection (tiered).** *Always:* `color-scheme` on `:root`,
no-flash script when toggle exists, every color token uses `light-dark()`
or paired values, shadows tokenised. *Smoke:* render both modes,
axe-core per-mode contrast, toggle visible in both. *Review Mode:*
dual-mode visual diff, toggle persistence, broken focus-ring per mode.
Single-mode-only output is a BLOCK in [banned-patterns.md](banned-patterns.md).

## Review Mode

**Opt-in.** Triggered by "review my UI" / "audit this design" / "check
accessibility", **or** by a stamped issue body containing `Review: required`
(set upstream by `/software-design` when AC mention accessibility,
contrast, or a design audit). Flow: WebFetch the Vercel Web Interface
Guidelines from `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`,
apply the **supplemental** checklist (~10 items, no Vercel duplications),
emit a `file:line` report, then a revised version with fixable issues
resolved.

Supplemental checklist: WCAG 2.4.11 / 2.4.13 specifics, ≥ 4.5:1 normal
and ≥ 3:1 large/UI; every spacing/color/shadow/radius references a named
token; layout tested at 320 / 768 / 1280; `scroll-margin-top` for
fixed-header anchors; no `Lorem ipsum`; loading and empty states defined;
every visible choice traces to `docs/design/direction.md`; light and
dark both tuned; `prefers-reduced-motion` honoured; slop-font tripwire clean.

## Output Format

Fenced blocks with language tags. Token definitions in a separate
`tokens.css` / theme block first, then referenced in component code.
Inline comments only where *why* is non-obvious. Offer to split outputs
that exceed ~200 lines.
