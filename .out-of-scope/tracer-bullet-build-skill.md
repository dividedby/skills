# Tracer-Bullet Development as a Standalone Skill

This repo will **not** publish a separate engineering skill for "tracer-bullet
development" / "build vertical slices, not horizontal layers" during the build
phase. The discipline is real and valued — it is just already delivered by the
existing pipeline rather than by a new skill.

## Why this is out of scope

The plan → backlog → build pipeline already enforces tracer-bullet development,
at the issue grain:

- **`to-prd` / `to-issues`** distill a plan into independently-grabbable issues
  using tracer-bullet _vertical slices_. Decomposition is already vertical.
- **`software-design`** rewrites each issue down to **one observable behavior**,
  with TDD notes that name an **entry point** and a **must-not-test** boundary.
  A one-behavior issue with an entry point and an explicit non-goal _is_ a
  vertical slice with a built-in stopping signal.
- **`software-design` + #97**** orders the whole set
  **tracer bullet → core behavior → edge cases → integration**. (The ordering
  rule already lived in `issue-shape.md`; #97 wires the workflow to invoke it.)

So an agent working the backlog in order — one thin issue at a time via `tdd` —
is already doing tracer-bullet development. The motivating failure mode (an agent
building all horizontal layers before validating any end-to-end path) is
_structurally_ prevented when issues are thin slices built in tracer-bullet
order. A standalone skill would re-state, at a fourth location, a discipline the
pipeline already produces.

The only residual the request identifies is **build-time drift _within_ a single,
already-thin issue** (an agent gold-plating a horizontal layer inside one
ticket). That is `tdd`'s turf — construction within an issue — and `tdd` is a
**globally-installed skill, not a file in this repo**, so it is not ours to edit
here. It is also largely covered already: "one observable behavior + acceptance
criteria" is the stopping signal.

## If this is ever reconsidered

The bar to revisit is a demonstrated gap the pipeline does _not_ close — e.g.
real runs where, despite thin tracer-bullet-ordered issues, `tdd` agents
repeatedly expand a single issue into horizontal layers. That would be evidence
for a small **build-time** reminder in `tdd` (upstream), not for a new published
skill in this repo.

## Prior requests

- #100 — "New engineering skill: tracer-bullet development for AI-assisted
  feature building" (`source:agent-research`; sources:
  mattpocock/practices/tracer-bullets-over-horizontal-layers,
  amp/practices/trust-is-a-passing-test-suite)
