# Closed waves collapse then prune; the census is an execution view, GitHub is the archive

The roadmap census started as a **full record**: a closed issue's row stayed in
the table as `Status: Done`, never deleted — the doc was meant to be the complete
ledger of every issue, open or closed. In a long-lived repo this grows the census
unbounded, and the bulk of it is closed work no agent will ever pick. The maintainer
wanted the doc to stay **equally human-readable and agent-actionable** — the active
backlog visible at a glance, not buried under historical `Done` rows — while
mirroring the Idea Inbox's collapsed-`<details>` progressive-disclosure pattern.

## Decision

The census is an **execution view, not the archive.** Closed work collapses, then
prunes, on a **wave granularity**:

1. **Closed wave → collapse.** When every issue in a Wave is closed, wrap that
   Wave's census rows in a collapsed
   `<details><summary>Closed wave W# — <theme></summary>…</details>`. Open waves
   and the active census stay **inline** (no `<details>`), so the working backlog
   is always the first thing read.
2. **Newer wave active → prune.** Once a *newer* Wave becomes active, the
   collapsed wave's rows are **deleted**, leaving a **one-line wave summary** in
   its place and **bumping a cumulative closed-count integer** in the Burn-down.
   The integer is the durable total: pruning rows never loses the count.
3. **Archive = none.** Nothing is copied elsewhere first. **GitHub retains closed
   issues permanently** and **git history holds every pruned row**, so the census
   carries no obligation to be the record — it carries the obligation to be the
   *fast read*.

## Supersedes the no-delete decision

This **reverses** the prior "closed rows are never deleted" rule, in both places it
was written:

- The **anti-pattern** "Deleting a closed issue's row" in
  `skills/engineering/roadmap/SKILL.md` (the reconcile Anti-Patterns section) — a
  closed wave's rows are now *expected* to be pruned once a newer wave is active.
- The **template Self-update protocol** rule "Closed → `Status: Done` (keep the
  row)" in `skills/engineering/roadmap/templates/roadmap.md` — closed is still set
  to `Done`, but the row is no longer kept indefinitely; it collapses with its
  wave and prunes when the wave is superseded.

The anti-pattern is *narrowed*, not dropped: deleting a closed row **ad hoc, before
its wave is collapsed-and-superseded, or without bumping the cumulative count** is
still wrong. The legitimate delete is the wave-based prune described above.

## Why this is consistent with 0020 / 0021 / 0022

- **0020 (working-tree doc, mirrored read-only).** The doc stays authoritative;
  pruning is a working-tree edit landed through the same reconcile PR. The
  CI-rendered mirror carries the `<details>` through untouched (it is a pure
  render), so the glance-from-web property is preserved with the collapse intact.
- **0021 (inbox vs roadmap — everything registers in the roadmap).** Registration
  is unchanged: an issue still enters the census when filed. Pruning happens only
  *after* close and *after* a newer wave supersedes it, so nothing un-registers a
  live issue. The drift nudge's "unfiled open" check is unaffected — it flags only
  **open** issues with no row, and a pruned row is always a **closed** issue.
- **0022 (reconcile auto-applies on a green gate).** Collapse-and-prune is a
  **Tier-1 mechanical** repair — deterministic, no judgment — so it auto-applies on
  the reconcile PR like every other Tier-1 edit. The cumulative count is derivable
  from prior census + this reconcile's `gh` state, carrying no new data source.

## Rejected alternatives

- **Per-issue retention (prune each row N reconciles after it closes).** Splits a
  wave's history across the inline census and `<details>` mid-stream, and needs a
  per-row age the table doesn't carry. Wave granularity keeps a closed wave intact
  until it is wholly superseded. Rejected.
- **An archive file (`docs/plans/roadmap-archive.md`).** Duplicates what GitHub and
  git history already retain, and adds a second doc to keep honest. Rejected in
  favor of archive = none.
- **Sprints / points on waves.** Out of scope here — deferred to the Idea Inbox
  ("points on named Waves", #91). This ADR adds no point columns.
