# software-design runs after to-issues, not before

`software-design` runs **after** `/to-issues` has published the backlog
(`/to-prd → /to-issues → /software-design → /tdd`), enriching each existing
issue body in place rather than designing modules first and letting
`/to-issues` mint issues from a settled design. This ordering is dictated by
the I/O contracts of the **immutable upstream skills** — `to-prd`, `to-issues`,
and `tdd` are Matt Pocock's skills (installed via `/setup-matt-pocock-skills`),
not editable in this repo — so `software-design` must adapt to them, not the
reverse.

**Amendment (2026-07-02, #520):** the chain's terminal step is `/tdd` **or**
`/implement` — both are terminal implementation skills per the workflow chain
convention set in #326 (`to-prd / to-issues / tdd / implement`). The chain
above names `/tdd` alone because it predates that convention; nothing else in
this ADR's reasoning changes.

**Why after, not before.** The reorder ("settle the design, then build issues
from it") is appealing but collapses on two facts:

- `to-issues` mints issues in **its own template** (Parent / What to build /
  Acceptance criteria / Blocked by) and can't be taught the module-assigned,
  TDD-ready format.
- `/tdd` consumes **only the issue body** (plus `CONTEXT.md` and ADRs). It never
  reads `docs/design/`. Its planning step re-derives interfaces itself.

So the only place `software-design` can deposit design-derived guidance that
`/tdd` will actually see is **inside the issue body**, and the only way to get
it there is to rewrite the issue *after* `to-issues` creates it. A design-first
ordering would write the TDD strategy into a Design Plan that nothing downstream
opens, and would *still* require a post-`to-issues` enrichment pass to reach
`/tdd` — designing twice for no net saving.

**The issue rewrite is enrichment, not waste.** `to-issues` produces *what to
build + acceptance criteria*; `software-design` upgrades that to
*module-assigned, TDD-ready behavior*. That pass is the skill's core value, not
redundant churn — the surface objection ("we're overwriting `to-issues`' work")
misreads a deliberate refinement as rework.

**Rejected alternative.** Running `software-design` between `/to-prd` and
`/to-issues` so issues are born TDD-ready. Rejected: `to-issues` writes its own
template and `/tdd` reads only the issue, so design-derived detail can't reach
implementation without a later in-issue rewrite — which is the current ordering.
