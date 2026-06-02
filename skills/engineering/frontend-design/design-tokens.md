# Design Tokens

The merged token taxonomy `/frontend-design` references during **Design
Language Instantiation** (Step 5 of the Iteration Loop), when the committed
direction in `docs/design/direction.md` is translated into a concrete
`tokens.css` (or Tailwind theme block) at the *Token authority path*.

Tokens are the bridge between *direction* (intent, in prose) and
*components* (code). Components reference tokens only — never raw values.
Raw values in component code are AI-slop and are flagged by the post-
generation audit.

Four taxonomies:

1. **Color** — token names, OKLCH authoring, `color-mix()`, `light-dark()`.
2. **Type** — M3 roles, fluid sizing, fallback metrics, balance/pretty wrapping.
3. **Motion** — spring physics for spatial, duration+easing for non-spatial.
4. **Spacing & Depth** — named scales for spacing, shadow/elevation, radius.

---

## 1. Color

### Canonical token list

Adopt the shadcn `*-foreground` idiom verbatim (drop the `--color-`
prefix when writing CSS variables — `background`, not `--color-background`).
Every background-carrying token pairs with a `-foreground` partner that is
guaranteed to meet contrast against it.

```
background / foreground
card / card-foreground
popover / popover-foreground
primary / primary-foreground
secondary / secondary-foreground
muted / muted-foreground
accent / accent-foreground
destructive / destructive-foreground
border
input
ring
chart-1 .. chart-5
sidebar / sidebar-foreground
sidebar-primary / sidebar-primary-foreground
sidebar-accent / sidebar-accent-foreground
sidebar-border
sidebar-ring
```

Optional state companions follow the same pairing rule:
`warning / warning-foreground`, `success / success-foreground`,
`info / info-foreground`.

Do **not** ship the older `error / warning / success / info` standalones
without their foreground partners; the bare names predate the idiom and
inevitably produce contrast bugs.

### Authoring in OKLCH

All color tokens are authored in **OKLCH**. OKLCH is perceptually uniform,
so a lightness step looks like a lightness step regardless of hue — which
hex and HSL fail at. Example:

```css
:root {
  --primary: oklch(0.62 0.18 264);
  --primary-foreground: oklch(0.98 0.01 264);
}
```

### Derivation via `color-mix()`

Derive hover/pressed/disabled/etc. states from base tokens using
`color-mix()` in OKLCH space — don't author a parallel token tree.

```css
--primary-hover:   color-mix(in oklch, var(--primary), black 10%);
--primary-pressed: color-mix(in oklch, var(--primary), black 18%);
--primary-muted:   color-mix(in oklch, var(--primary), var(--background) 70%);
```

### Light/dark pairing via `light-dark()`

Default mechanism is `light-dark()` with `color-scheme` declared on
`:root`. Class-swap is the documented fallback for tooling that doesn't
yet understand `color-scheme`.

```css
:root {
  color-scheme: light dark;
  --background: light-dark(oklch(0.99 0.005 80), oklch(0.16 0.01 80));
  --foreground: light-dark(oklch(0.18 0.01 80), oklch(0.96 0.005 80));
}

/* Fallback class-swap (kept for tooling without color-scheme support) */
.dark {
  --background: oklch(0.16 0.01 80);
  --foreground: oklch(0.96 0.005 80);
}
```

Single-mode-only output (no `light-dark()` and no class-swap) is a BLOCK
in `banned-patterns.md`.

### Other color rules

- `accent-color: var(--primary)` on `:root` so native form controls pick
  up the palette.
- Test under `forced-colors: active`; never rely on `background-image`
  alone to convey state.
- Saturated tokens on dark surfaces must be lightened — copying hex from
  a brand guide and using both modes verbatim produces failing contrast.
- WCAG 2.2 AA is normative: ≥ 4.5:1 for body text, ≥ 3:1 for large text
  and UI components. APCA is supplemental until WCAG 3 ships.

---

## 2. Type

### Roles, not sizes

Adopt **M3-style type roles**. Each component picks a role; the role
carries the size, weight, line-height, and tracking decisions.

```
display-lg   display-md   display-sm
headline-lg  headline-md  headline-sm
title-lg     title-md     title-sm
body-lg      body-md      body-sm
label-lg     label-md     label-sm
```

**Raw px in component code is AI-slop.** Components reference role tokens
only:

```css
.hero-headline { font: var(--display-lg); }   /* good */
.hero-headline { font-size: 56px; }            /* slop */
```

### Fluid and resilient primitives

All required during Step 5 instantiation:

- **`clamp()` on display roles** — fluid sizing tied to viewport without breakpoints.
  Example: `font-size: clamp(2.5rem, 4vw + 1rem, 4.5rem);`
- **Variable fonts** when available; `font-optical-sizing: auto`.
- **`font-display: swap`** for display/headline; `font-display: optional` for body (avoids FOUT on body copy).
- **Fallback metric overrides** on `@font-face` — `size-adjust`, `ascent-override`, `descent-override`, `line-gap-override` — so the system fallback occupies the same vertical space as the brand font. (Next.js `next/font` does this automatically.)
- **`text-wrap: balance`** on headings ≤ 6 lines.
- **`text-wrap: pretty`** on body copy.
- **`font-variant-numeric: tabular-nums`** on any numeric column (tables, dashboards, financials).

`leading-trim` / `text-box-trim` are forward-looking and optional today.

### Line length and line height

- **Line length**: 45–75ch. The split is **65–75ch** for long-form prose;
  **45–65ch** for UI / dense layouts. Never let prose span the full viewport.
- **Line height must be unitless** — `1.5`, never `24px` or `1.5rem`. Body
  text 1.5–1.65; display headings 1.05–1.2.

### Font choice

Direction-derived. The Named Direction Rule does the work — the chosen
direction in `docs/design/direction.md` names the typography intent that
constrains font choice. Inter, Geist, Roboto, and Arial are
**default-detection tripwires** during the post-generation audit: the
skill must state the direction-derived justification before emitting one.
Not a hard ban, but the bar is "the direction explicitly calls for it",
not reflex.

---

## 3. Motion

Motion tokens split by **what is moving**:

- **Spatial motion** (position, scale, layout) → **springs**.
- **Non-spatial** (opacity, color, blur) → **duration + easing**.

### Duration scale (non-spatial)

```
--motion-duration-instant: 80ms;   /* micro-feedback (toggle, ripple) */
--motion-duration-fast:    150ms;  /* < 150ms — micro-interactions */
--motion-duration-base:    240ms;  /* 200–400ms — page/component transitions */
--motion-duration-slow:    320ms;  /* 250–350ms — modal reveals, large panels */
```

Never exceed 500ms for UI feedback.

### Easing tokens (non-spatial)

```
--motion-ease-out:    cubic-bezier(0.2, 0, 0, 1);   /* enter */
--motion-ease-in:     cubic-bezier(0.4, 0, 1, 1);   /* exit */
--motion-ease-in-out: cubic-bezier(0.4, 0, 0.2, 1); /* position change */
```

**Plain `linear` is banned for spatial UI transitions.** It is correct
for continuous/looping motion (spinners, indeterminate progress, parallax,
opacity-only crossfades). The CSS `linear()` function (Baseline 2023) is
endorsed for **spring approximation in CSS without JS** — e.g.
`transition-timing-function: linear(0, 0.18, 0.5, 0.82, 1);`.

### Springs (spatial)

Use a spring library (Framer Motion, Motion One) or `linear()`
approximation. **Spring settle time must land in the same windows as the
duration scale** (< 150ms / 200–400ms / 250–350ms). A spring that wobbles
for 900ms is decoration, not motion.

```
--motion-spring-snappy:    { stiffness: 380, damping: 30, mass: 1 }
--motion-spring-considered:{ stiffness: 220, damping: 26, mass: 1 }
--motion-spring-still:     { stiffness: 140, damping: 22, mass: 1 }
```

### Hard rules

- **Animate `transform` and `opacity` only.** Animating `top` / `left` /
  `width` / `height` triggers layout; transform/opacity compose on the GPU.
- **Interruptible by default.** Mid-flight animations must accept a new
  target without jumping back to the start. Spring libraries handle this
  natively; CSS transitions need `transition` re-applied with the new value.
- All animations must respect `prefers-reduced-motion`. Provide a
  `@media (prefers-reduced-motion: reduce)` block that removes or
  simplifies every transition.

### Reach-for

- **View Transitions API** for route-level and large-scope transitions —
  cross-document on Chromium, same-document elsewhere.
- **Scroll-driven animations** via `animation-timeline: scroll()` or
  `view()` — for parallax, sticky reveals, progress indicators tied to
  scroll position. Falls back gracefully where unsupported.

### Negative rule: `will-change`

Apply `will-change` on intent (hover/focus) and remove after the animation
completes. **Never blanket-apply** `will-change: transform` to every
animated element — it creates an implicit GPU layer that consumes memory
and degrades scroll performance.

### Cross-reference: elevation in motion

When a token from the shadow/elevation scale (see Spacing & Depth) is the
animation target, treat the shadow change as spatial (use a spring or
`linear()` approximation) — a linear shadow ramp reads as a tech demo,
not a lift.

---

## 4. Spacing & Depth

Three named scales. Never write a raw value where a token would do.

### Spacing scale

```
--space-1:  0.25rem;
--space-2:  0.5rem;
--space-3:  0.75rem;
--space-4:  1rem;
--space-5:  1.5rem;
--space-6:  2rem;
--space-7:  3rem;
--space-8:  4rem;
--space-9:  6rem;
--space-10: 8rem;
```

`margin: 13px` is slop. So is `padding: 17px`.

### Shadow / elevation scale

A **compact named scale** of 5 levels. Illustrative values (per ADR 0002,
these are an example shape, not canonical numbers). `light-dark()` accepts
only a `<color>` argument, so wrap the *shadow color* in it — the same
mechanism as the color tokens — and keep the geometry shared across modes:

```css
:root {
  --shadow-sm:      0 1px 2px  light-dark(oklch(0.15 0.01 220 / 0.07), oklch(0.10 0.01 220 / 0.36)); /* hairline lift (cards at rest) */
  --shadow-md:      0 2px 6px  light-dark(oklch(0.15 0.01 220 / 0.10), oklch(0.10 0.01 220 / 0.44)); /* hover lift (interactive cards) */
  --shadow-lg:      0 4px 16px light-dark(oklch(0.15 0.01 220 / 0.12), oklch(0.10 0.01 220 / 0.52)); /* dropdown, popover */
  --shadow-xl:      0 8px 32px light-dark(oklch(0.15 0.01 220 / 0.16), oklch(0.10 0.01 220 / 0.60)); /* modal, large overlay */
  --shadow-overlay: 0 16px 56px light-dark(oklch(0.15 0.01 220 / 0.20), oklch(0.10 0.01 220 / 0.72)); /* full-screen overlay / scrim */
}
```

Dark-mode opacity runs 4–5× higher than light: a dark surface absorbs
ambient contrast, so a faint shadow simply vanishes against it and needs
far more opacity to register the same lift. Tune the `oklch` hue channel to
the direction's ambient palette during Step 5 (cool `220`, warm `40`,
neutral `0`) — a shadow tinted toward the surface reads more natural than
neutral black. If a mode needs different blur or offset (not just color),
fall back to the class-swap mechanism rather than `light-dark()`, which
cannot vary geometry.

Every component uses only named levels. Ad-hoc `box-shadow` values are a
WARN-tier slop signal during audit.

### Radius scale

```
--radius-sm: 0.25rem;   /* inputs, badges */
--radius-md: 0.5rem;    /* buttons, cards */
--radius-lg: 0.75rem;   /* dialogs, sheets */
--radius-xl: 1rem;      /* hero cards, large containers */
--radius-pill: 9999px;  /* pills, avatars */
```

Mixing arbitrary radii across components dissolves visual rhythm.

---

## Token authority

The Token authority path is recorded in `docs/design/direction.md`
(field #9). Step 5 writes the instantiated `tokens.css` (or Tailwind
theme block) to that path. Token values change without an ADR; only the
*direction* the tokens express is ADR-worthy (see
[`direction-doc-format.md`](direction-doc-format.md)).
