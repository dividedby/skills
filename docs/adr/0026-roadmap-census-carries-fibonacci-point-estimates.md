# Roadmap census carries Fibonacci point estimates; velocity is completed-points progress

[ADR 0023](./0023-closed-waves-collapse-then-prune-census-is-an-execution-view.md)
explicitly **deferred** "Sprints / points on waves" to the Idea Inbox ("points on
named Waves", #91) — it added no point columns. That idea drained as #244. Waves
are **priority buckets, not time-boxes** (the census is read top wave first; a wave
carries no start/end date), so any points treatment must answer "how much effort is
left in this wave?" without implying a calendar sprint the model deliberately
declined.

## Decision

The census gains a **`Points`** column, inserted **after `Wave`**:

1. **Fibonacci estimate.** Points are a Fibonacci effort estimate (`1` · `2` · `3`
   · `5` · `8`), `—` when unestimated. Per-item; estimation stays optional.
2. **Burn-down rolls up per-wave completed/total points.** For each wave, completed
   is the sum of points on `Done` rows, total the sum across the wave's rows —
   recomputed from the `Points` + `Status` columns every reconcile (no new data
   source), exactly like the open-by-wave line.
3. **Cumulative completed-points integer carried across prune.** A running all-time
   completed-points integer in the Burn-down is **bumped on each wave prune**,
   mirroring the cumulative closed-count of ADR 0023 — pruned rows are gone, so the
   integer is not recomputable from the table and must carry forward.
4. **"Velocity" means completed-points progress, NOT points-per-time.** The signal
   is "how far through the estimated work are we" (completed/total), deliberately
   not a rate. There is no wave time axis, and reconcile's only live signal is
   census text plus one `gh` state call (number/state) — no `closed-at` dates to
   build a rate from. Adding a time axis was considered and **rejected**: it would
   reintroduce the calendar-sprint model the idea declined.

## Why this is consistent with 0023 / 0025

- **0023 (cumulative count carried across prune).** The completed-points integer
  is the points analogue of 0023's closed-count integer — same bump-on-prune,
  never-recompute discipline, same reason (rows are deleted, the total must
  survive). Per-wave completed/total is a pure projection like open-by-wave.
- **0025 (cells are thin pointers).** `Points` is a single token (a number or `—`),
  the thinnest possible cell — it adds no narrative to the row.
- **Both parsers resolve columns by header name.** `roadmap-drift-nudge.py` and
  `roadmap-guard.py` resolve census columns by **header name** (`#`/`Issue`,
  `Status`), not by fixed index, so inserting `Points` after `Wave` shifts no index
  and breaks neither parser. A numeric `STATUS_COL` *override* in the nudge is the
  one exception — a pinned index must be bumped by its setter.

## Consequences

- **No hard guard invariant on Points.** Estimation is optional per row (`—`), so
  unlike the Burn-down open-count check there is no guard invariant requiring Points
  to be present or to sum to anything. The points rollup is informational.
- **Existing live roadmaps adopt points organically.** No migration: a live census
  picks up the `Points` column and per-wave rollup on its next reconcile, rows
  estimated as they are touched.

## Rejected alternatives

- **Points-per-time velocity (a rate).** Needs a wave time axis and per-issue
  `closed-at` data reconcile does not fetch, and reintroduces the calendar-sprint
  model #91 declined. Rejected in favor of completed/total progress.
- **A points invariant in `roadmap-guard`.** Would force every row to be estimated.
  Estimation is optional by design (`—`); a hard check defeats that. Rejected.
