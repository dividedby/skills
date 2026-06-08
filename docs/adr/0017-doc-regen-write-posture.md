# doc-regen edits the working tree and writes additive issue comments, but never commits or closes

The `doc-regen` skill (issue [#154](https://github.com/dividedby/skills/issues/154))
reconciles a repo's roadmap census with live GitHub issue state. Its original
proposal drew a hard boundary — *"never commits, never mutates issues on
GitHub"* — putting it alongside the propose-only AFK loops of
[ADR 0003](./0003-skill-improvement-workflows-propose-via-issues.md).

That boundary is too tight for the skill's actual job. The roadmap is the **source
of record**: the work-the-roadmap protocol points the working agent at each issue
for authoritative scope, and reads the **full issue including comments**. If the
reconciler may not touch issues, the issues drift out of sync with the roadmap it
maintains — an unblocked issue keeps a stale "blocked by #X" note, a re-routed
item carries no record of the change — and "just read the roadmap" breaks at the
issue. Keeping the roadmap honest *requires* keeping the issues honest too.

## Decision

`doc-regen` has a **graded write posture**, mirroring the interactive-vs-loop
split `staleness-audit` already uses for its apply station:

1. **Working tree — edit for review, never commit.** All roadmap edits (and, in
   bootstrap, the scaffolded hooks/settings) are written to the working tree. The
   human reviews `git diff` and commits. Same as ADR 0003's producer/decider line.
2. **Issues — additive only, in an interactive run.** The skill **may add/update
   comments** (unblock notes, routing, sequencing, tier-2 slotting decisions) and
   **record blocker/dep changes**. It **may not close an issue** and **may not
   rewrite a body** — closing stays a human act on a tier-3 *recommendation*, and
   bodies are human-authored. Comments are additive and trivially reviewable.
3. **Loop-suppression invariant.** If `doc-regen` is ever wired into an unattended
   loop, the issue-write surface is **suppressed → propose-only**, exactly as the
   `staleness-audit` cron suppresses its apply station. The additive-issue-write
   surface is for an interactive, watched run, never an AFK one.

## Why this does not violate ADR 0003

ADR 0003 governs the **unattended proposal loops** — the producer that runs AFK
must only propose. `doc-regen` is a **maintainer-invoked, interactive** skill;
its additive writes happen under a watching human who reviews the diff and the
comments. The loop-suppression invariant preserves ADR 0003 exactly where it
applies: the moment this skill runs unattended, it drops back to propose-only.
This is the same shape ADR 0003's amendment already blesses for `staleness-audit`
(mutates interactively, report-only on the cron).

## Consequences

- The SessionStart drift nudge tells the human "it edits the working tree for
  review and writes additive issue comments; it never commits" — the posture is
  stated where the skill is invoked.
- Tier-3 ("looks already done") stays **report-only**: it never writes the
  roadmap and never touches issues, so the human keeps the close decision.
- A future loop wrapper must assert the suppression (no `gh issue comment`,
  propose-only) the same way the staleness loop grants no `Edit`/`Write`.

## Rejected alternatives

- **Never touch issues (the original #154 boundary).** Leaves issues drifting
  from the roadmap that points at them; the source-of-record property fails at
  the issue. Rejected because the whole pattern exists to kill that drift.
- **Full bidirectional sync, incl. auto-close and body edits.** Auto-closing on
  inference removes the human gate tier-3 deliberately preserves, and editing
  human-authored bodies is high-risk and hard to review. Out of scope; closing
  and body edits stay human.
