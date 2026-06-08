---
name: doc-regen
description: >
  Reconcile a repo's human-readable roadmap (a master census of every issue) with
  live GitHub issue state, so the doc stays trustworthy enough to be the only thing
  you read to pick the next task. Detects state and routes: bootstrap the whole
  pattern in a fresh repo, migrate a legacy planning doc into the canonical format,
  or reconcile an existing roadmap. Edits the working tree for review and writes
  additive issue comments; never commits, never closes issues. Use when a
  SessionStart drift nudge fires, on a cadence, when standing up the roadmap pattern,
  or any time the census looks stale against `gh`.
---

# Doc Regen

A repo can make one Markdown roadmap its **execution source of record**: a master
census with one row per issue (status, wave, owner, skill routing, deps) that is
the single place you go to pick the next thing to work on. Two cheap hooks keep
it from rotting — a PreToolUse guard forces an issue-referencing commit to touch
the roadmap (in-branch freshness), and a SessionStart nudge reports *out-of-band*
drift (issues opened/closed via `gh`/web between sessions, which the commit guard
structurally cannot see). This skill is the **reconcile half**: it repairs the
drift the nudge reports, and stands the whole pattern up where it does not exist.

It is deliberately **propose/edit-for-review** on the repo and **additive-only**
on issues — same governance posture as
[ADR 0003](../../../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md)
and [ADR 0017](../../../docs/adr/0017-doc-regen-write-posture.md): it edits the
working tree and writes issue *comments*, but never commits, never closes an
issue, and never rewrites an issue body. A human reviews `git diff` and decides.

## The front door — detect state, then route

The first thing every run does is decide *which mode* it is in, by inspecting the
configured roadmap path (`ROADMAP`, default `docs/plans/roadmap.md` — the same
constant the hooks use):

1. **Canonical roadmap present** (the path exists and parses as a census) →
   **reconcile**. The common case; the rest is just keeping it honest.
2. **No roadmap, but a legacy planning doc exists** (an older `ROADMAP.md`, a
   `docs/plan*`, a TODO/tracking doc, a project board exported to markdown) →
   **migrate**. Adapt the existing artifact into the canonical format.
3. **Nothing** → **bootstrap**. Stand the whole pattern up from scratch.

Distinguishing (2) from (3) is a judgment call — look for any human-maintained
list of work before concluding there is nothing to adapt. When unsure, treat it
as migrate and *propose* the mapping rather than overwriting silently.

## Bootstrap — stand the pattern up (turn-key)

Run in a repo that has issues but no roadmap. Scaffold everything to the working
tree for review (never committed), in one pass:

- **Drop the roadmap.** Copy [`templates/roadmap.md`](templates/roadmap.md) to
  `ROADMAP`, fill the project name, and **backfill one census row per open
  issue** from `gh issue list` — then run the reconcile tiers below to set
  statuses, waves, and deps so the doc lands populated, not empty.
- **Wire the two hooks.** Copy [`templates/roadmap-guard.py`](templates/roadmap-guard.py)
  (PreToolUse) and [`templates/roadmap-drift-nudge.py`](templates/roadmap-drift-nudge.py)
  (SessionStart) into `.claude/hooks/`, `chmod +x`, and **edit each file's config
  block** to the repo's roadmap path and census column indices. Ship
  [`templates/roadmap-drift-nudge.test.py`](templates/roadmap-drift-nudge.test.py)
  beside the nudge and run it to confirm the parser config matches the table.
- **Register the hooks in `settings.json`** (the snippet is in the onboarding
  runbook). A project-scope hook may redeclare a global guard for CI/AFK parity
  ([ADR 0013](../../../docs/adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md)).

Bootstrap writes files but **commits nothing** — finish by telling the human to
review `git diff` and the new untracked files, then commit.

## Migrate — adapt a legacy doc into the canonical format

Run when an older planning artifact exists. The goal is to *preserve* the human's
content while reshaping it onto the census:

- Read the legacy doc and map its entries onto canonical rows (issue #, status,
  wave, owner, skill, deps), inferring the closest canonical `Status` for each
  legacy state. **Preserve prose** — carry freeform legacy notes into the `Notes`
  cell or a section above the census; do not discard human context.
- **Propose the mapping before reshaping.** Migration edits a human-authored
  artifact, so state the proposed census (and any ambiguous legacy→canonical
  status mappings) for review *first*, then write it.
- Once the canonical roadmap exists, fall through to reconcile to fill gaps
  against live issue state, and wire the hooks as in bootstrap.

## Reconcile — repair drift in three tiers

The core loop. Gather state once, then work three tiers of increasing judgment
and decreasing write-authority.

### Gather state
One `gh issue list --state all --json number,state,title,labels`; read and parse
the census (the parser keys off column *index*, per the hook's config — do not
re-derive it from a hardcoded schema); `git log` / `git diff` / grep the working
tree for the tier-3 cross-check. One network call to `gh`; no product or live data.

### Tier 1 — mechanical (write to the working tree)
Deterministic repairs that need no judgment, applied directly:
- A closed issue whose row is not `Done` → set `Status: Done` (**keep the row** —
  closed issues stay in the census as `Done`, never deleted).
- A row whose blocking `Deps` have all closed → *italicize* the satisfied deps and
  flip `Blocked` → `Backlog`/`Next` per the doc's own ordering rules.
- Recompute wave and `Next` markers per the roadmap's stated ordering.

### Tier 2 — semantic (propose the row, then write)
Newly-opened issues with no census row: slot each in with an **inferred** wave,
cluster, owner, skill routing, and deps. Because these are judgment calls, **state
the proposed row and the reasoning first**, then write it. Do **not** flag a child
that is already aggregate-covered by an epic/PRD parent row as "unfiled" — the
nudge over-reports those by design (it can't see aggregate coverage).

### Tier 3 — code cross-check (report-only, never write)
For each open row, look for working-tree evidence the fix already landed (a merged
file, a closed-looking implementation). List the suspects with a confidence note
for a human to confirm and close. **This tier never edits the roadmap and never
touches issues** — "looks done" is the human's call, by construction.

### Issue writes — additive only
As reconcile repairs the roadmap, keep the *issues* honest too, since the roadmap
points the working agent at them for authoritative scope (and the work-the-roadmap
protocol reads the full issue **including comments**). The write surface is
strictly additive ([ADR 0017](../../../docs/adr/0017-doc-regen-write-posture.md)):
- **Add/update a comment** when a dep closes and unblocks an issue, when routing
  or sequencing changes, or to record a tier-2 slotting decision — so the next
  agent reads it on the issue, not just in the roadmap.
- **Record blocker/dep changes** as comments and in the roadmap's `Deps` cell.
- **Never close an issue, never rewrite a body.** Closing stays a human act on a
  tier-3 recommendation; bodies are human-authored.

### Finish
Summarize the three tiers (what was auto-written, what was proposed, what tier-3
flags for the human). Tell the human to review `git diff <ROADMAP>` and commit.
**Never commit, never close issues.**

## Boundaries

- **Static.** `gh` + working tree only — no product or live data, no network
  beyond the one `gh issue list` call.
- **Never commits.** Edits the working tree for review; the human commits.
- **Additive on issues; report-only on tier-3.** Comments and dep notes only;
  no close, no body rewrite; tier-3 never writes at all.
- **Loop-suppression.** If ever wired into an unattended loop, the issue-write
  surface is suppressed → propose-only, mirroring `staleness-audit`'s apply
  station ([ADR 0017](../../../docs/adr/0017-doc-regen-write-posture.md)). The
  additive-issue-write surface is for an interactive, watched run.
- **Complements, does not replace, `roadmap-guard.py`.** The guard keeps the doc
  fresh *inside* a PR; this skill repairs *between-PR* drift.

## Anti-Patterns

- **Deleting a closed issue's row.** Closed issues stay as `Done` rows — the
  census is the full record, not just the open set.
- **Flagging an aggregate-covered child as unfiled.** A child tracked by an
  epic/PRD parent row is represented; only genuinely unrepresented open issues
  are tier-2 candidates.
- **Auto-closing an issue, or editing its body.** Closing is a human act on a
  tier-3 recommendation; issue writes are additive comments only.
- **Committing the reconcile.** It edits the working tree for review; a human
  reviews `git diff` and commits.
- **Re-deriving the census schema from a hardcoded shape.** Parse by the hook's
  configured column index so the skill adapts to the repo's table.
- **Restating issue scope in the roadmap.** The census routes and orders; the
  issue body (plus comments) is authoritative for scope (ADR 0002 — principle,
  not a fixed column layout).
