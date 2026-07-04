# Wire skill-divergence-audit as a recurring, propose-only loop

> **Status: Accepted** — maintainer-ratified WIRE decision on issue [#522](https://github.com/dividedby/skills/issues/522) (2026-07-04), which absorbed Epic B [#515](https://github.com/dividedby/skills/issues/515).

## Context

`skills/meta/skill-divergence-audit` has existed since before this ADR, with
its own `SKILL.md`, a pure-function classifier (`lib/divergence.py`), and a
guarded CLI seam (`lib/cli.py`) reusing the sibling `apply-agent-research`
skill's `sanitizer` and `proposal_gate`. Five docs and its own frontmatter
described it as a "recurring loop" — but it had never actually run: no
workflow, no harness prompt, and zero `source:skill-audit` issues filed,
ever (independently re-verified 2026-07-02 via
`gh issue list --search "label:source:skill-audit" --state all` → empty).

Issue #522 (absorbing #515's audit evidence and #530's execution scope)
framed the decision as binary: wire it as a real scheduled loop, or delete the
dormant pipeline per this repo's delete-lean posture. The case for wiring:
the capability it promises is real and the drift it detects is live — Matt
shipped a new `research` skill 2026-07-01 with nothing here noticing, and
upstream moved roughly 100 commits in June. The case for deleting: a pipeline
that sat dormant 5+ weeks is dead weight, and wiring adds a fifth cron loop to
the cost surface.

Sequencing note: the decision was briefly deferred pending #529's overlap
sweep (measured churn vs. upstream), then ratified WIRE on 2026-07-04 once
that data landed — "on data, not posture," per the 2026-07-02 grilling comment
on #522.

## Decision

**Wire `skill-divergence-audit` as a recurring, propose-only scheduled loop.**

- `.github/workflows/skill-divergence-audit.yml` runs the skill on a
  hash-staggered 3×/week cron (`50 2 * * 1,3,6` UTC), inheriting model
  (`claude-sonnet-5`, exact pin) and per-run budget (`$4.00`) from the
  `apply-agent-research` / `improve-codebase-architecture` sibling loops per
  [ADR 0019](./0019-proposal-loops-file-a-budgeted-ranked-top-k.md).
- Unlike those two siblings, this loop is **host-only**: `dividedby/skills` is
  both the tracker and the skill catalog under audit, so there is no
  downstream-consumer shape and no thin-caller-stub / reusable-body split. The
  harness and the skill are read directly from the checkout — [ADR
  0014](./0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)'s
  fetch-fresh intent (never let a vendored copy drift from its source) is
  satisfied trivially, since the source *is* this checkout.
- Filing follows the same producer/decider split as every proposal loop in
  this repo ([ADR 0003](./0003-skill-improvement-workflows-propose-via-issues.md)):
  the agent never commits or edits, and its only mutation is filing through
  the skill's own guarded `lib/cli.py file` (leak guard + ≤1-per-run gate
  enforced in code), same discipline as `apply-agent-research` — not the
  harness `publish`-parses-`<output>` seam `improve-codebase-architecture`
  uses.
- `harness/prompts/skill-divergence-audit.md` supplies the concrete wiring
  (paths, tool-use constraints) and defers to the skill's own `SKILL.md` for
  the classify/gate/file mechanics, so the skill file stays the single source
  of truth.

**Code-level fix bundled with the wiring:** `lib/divergence.py`'s Pass 2
previously classified every one of `CONTEXT.md`'s ~11 deliberately-deleted,
soft-depended-on `mattpocock/skills` skills as `MISSING_HERE` on every run —
noise, not signal, since that gap is the intended posture
([ADR 0024](./0024-lean-on-upstream-skills-soft-depend-over-reinvent.md)).
`SOFT_DEPENDENCY_SKILLS` (sourced from `CONTEXT.md`'s "Upstream
soft-dependencies" list) now excludes them from Pass 2 before the loop ever
runs unattended.

## Out of scope

`#514`'s official-catalog (`anthropics/claude-plugins-official`) sweep as a
**second divergence axis** is explicitly deferred — it is a separate,
one-shot decision tracked on #514, not gated on this ADR. This loop's first
run continues to compare only against `mattpocock/skills` + the
`agent-research` KB, as `divergence.py` already does.

## Consequences

- `skill-divergence-audit` joins the reference cadence in
  `docs/agents/workflow-authoring.md` as a fifth loop; the maintainer's
  cross-repo `COST_SURFACE` onboarding (agent-research) is a separate,
  parallel step, not part of this repo's diff.
- A future decision to add the official-catalog axis (#514) has a wired
  carrier to land in, rather than needing to wire a new loop from scratch.
- If this loop sits dormant again (no runs, no issues) past a reasonable
  window, #532 (loop-liveness monitoring) is the intended guard — not a
  second silent-dormancy period followed by another delete-or-wire debate.
