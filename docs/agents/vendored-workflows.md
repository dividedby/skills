# Vendored Claude-powered Workflows

A reference map of the two vendored **proposal-loop** workflows across the repos
that run them: cron slots, timing, per-run budget, issue caps, and cross-repo
dependencies. It doubles as the reference surface for
[#365](https://github.com/dividedby/skills/issues/365) (guard envelope drift) and
[#366](https://github.com/dividedby/skills/issues/366) (reusable workflows to
shrink the envelope).

**Loop hosting model (post #382):**

| Loop | What lives per-repo | What lives in skills |
|---|---|---|
| `improve-codebase-architecture` | Thin caller stub (cron + `uses:` + tag + `permissions` grant) | `workflow_call` reusable body (`-reusable.yml`) |
| `staleness-review` | Thin caller stub (cron + `uses:` + tag + `permissions` grant) | `workflow_call` reusable body (`-reusable.yml`) |

Consumers pin the reusable bodies at tag `@claude-loops-v1`. The skills repo
uses a local-path `./` ref (canary — always runs the latest body).

**Caller stubs must grant `permissions: { contents: read, issues: write }`** on
the calling job. A called workflow can't be granted more token scope than the
caller holds, and every repo's default workflow permission is read-only — without
the grant the body's `issues: write` exceeds the caller's token and the run
**startup-fails**. The reusable body also declares the same `permissions`; the
two must agree.

**Snapshot date:** 2026-06-20 — live divergence check landed via the
`workflow-drift` job in
[`fleet-drift.yml`](../../.github/workflows/fleet-drift.yml)
(#365, weekly Sun 04:00 UTC, central in skills). The scheduled job reads each
consumer repo's vendored files via the GitHub Contents API, checks structural
anchors (anchor-presence, not full normalization), and opens a `workflow-drift`
issue in dividedby/skills for any drifted repo. To refresh this table, re-read
`.github/workflows/{improve-codebase-architecture,staleness-review}.yml`
in each repo.

**Tag-vs-main + pin-drift check** — the same job also resolves the
`claude-loops-v1` tag to its current commit and (a) diffs each reusable body's
tag-pinned content against `main` (one shared issue, fleet-wide, when the tag
lags), and (b) resolves each consumer's own `uses:` pin — a tag literal or a
40-char SHA with a trailing `# claude-loops-v1` comment — and diffs the
resolved content against `main` (folded into that consumer's existing
`workflow-drift` issue) (#524). Every consumer pins the `@claude-loops-v1` tag
literal, so `REPO_SKIP_ANCHORS` is empty and no stub is
exempted from the literal anchor check. The pin-drift lane still resolves a
40-char SHA (so a stray SHA pin's drift is still caught), but none is in use.

**Label-doc drift check** — companion detector landed via the `label-drift` job
in [`fleet-drift.yml`](../../.github/workflows/fleet-drift.yml)
(#415, weekly Sun 04:00 UTC — same run as workflow-drift, independent job).
Reads each consumer's `docs/agents/triage-labels.md` and `docs/agents/labels.md`
via the GitHub Contents API; classifies one of four drift shapes per repo; opens a
`label-drift` issue in dividedby/skills naming `setup-dividedby-skills` as the
fixer. Report-only — never mutates a consumer repo. Requires the same
`ISSUES_TOKEN` secret (with `DRIFT_CHECK_TOKEN` as Option-B fallback) as workflow-drift.

**Idea-inbox drift check** — companion detector landed via the
`idea-inbox-drift` job in
[`fleet-drift.yml`](../../.github/workflows/fleet-drift.yml)
(#488, weekly Sun 04:00 UTC — same run as workflow-drift and label-drift,
independent job). Reads each carrier repo's `docs/agents/idea-inbox.md` via the
GitHub Contents API; checks eight canonical structural anchors (breadcrumb, six
drain steps, rolling-window section); opens an `idea-inbox-drift` issue in
dividedby/skills naming `setup-dividedby-skills` as the fixer; references #489
for the one-time bulk reconciliation of existing drift. Report-only — never
mutates a carrier repo. Requires the same `ISSUES_TOKEN` secret as
workflow-drift and label-drift.

**Reading the crons:** schedules are UTC (authoritative). **CT** is shown for CDT
(Mar–Nov, UTC−5); **subtract 1h in CST** (Nov–Mar). Day codes: `* * 6` =
Saturday, `* * 1` = Monday, `* * 3` = Wednesday. Rows are ordered by UTC time within each table.

## Presence matrix

| Loop | skills | moodreader | goodreads-bot | dokdiv |
|---|:--:|:--:|:--:|:--:|
| `improve-codebase-architecture` | ✓ | ✓ | ✓ | — |
| `staleness-review` | ✓ | ✓ | ✓ | ✓ |

Repo roles: **skills** = host (carries the harness in-tree and the reusable
`workflow_call` bodies); **goodreads-bot** = deployed app (default branch
`staging`); **moodreader** and **dokdiv** = consumers. dokdiv's cron slot is not
tabulated below.

## `improve-codebase-architecture` — Mon/Wed/Sat (3×/week)

| Repo | cron (UTC) | CT (CDT) | timeout | budget | issues/run |
|---|---|---|---|---|---|
| moodreader | `3 0 * * 1,3,6` | Sun/Tue/Fri 19:03 | 20m | $3 | 1 |
| skills | `5 0 * * 1,3,6` | Sun/Tue/Fri 19:05 | 20m | $3 | 1 |
| goodreads-bot | `11 3 * * 1,3,6` | Sun/Tue/Fri 22:11 | 20m | $3 | 1 |

- **Issue cap:** flat cap of 1 estate-wide, no per-repo override, propagates via the fetched-fresh harness. Reference [ADR 0019](../adr/0019-proposal-loops-file-a-budgeted-ranked-top-k.md) (as amended 2026-06-30).
- Uses the harness **`publish` seam** (cap = `MAX_PROPOSALS`, [ADR 0019](../adr/0019-proposal-loops-file-a-budgeted-ranked-top-k.md)).
- Depth rubric fetched fresh from `mattpocock/skills@main`
  ([ADR 0020](../adr/0020-arch-review-fetches-depth-rubric-fresh-and-adds-simplification-legibility-lenses.md)).
- Proposal bodies include a **Design-tension section** — 2–3 candidate-specific
  competing constraints, a sketch under each, and a tension statement — as
  competing-constraint decision-support for the human triaging before implementation
  (ADR 0020, second amendment; async adaptation of DESIGN-IT-TWICE).

## `staleness-review` — first Monday of the month

| Repo | cron (UTC) | CT (CDT) | timeout | budget | issues/run |
|---|---|---|---|---|---|
| goodreads-bot | `7 13 * * 1` | Mon 08:07 | 20m | $3 | 1 |
| skills | `8 13 * * 1` | Mon 08:08 | 20m | $3 | 1 |
| moodreader | `10 13 * * 1` | Mon 08:10 | 20m | $3 | 1 |

- Gated to the **first Monday** via a `first-monday-gate` step (cron fires every
  Monday; the gate no-ops the other weeks).
- Uses the harness **`publish` seam**; cap = 1.
- Slots are **hand-chosen** in the 13:xx UTC band (this loop is not hash-staggered;
  the hash-stagger covers only the 3×/week loop). moodreader was realigned from an
  off-band `50 1` (Sun 20:50 CT) to `10 13` on 2026-06-20.

## Hash-stagger slots

Each cron minute is derived deterministically from `sha1("<repo>/<loop>")` within
a fixed band, so onboarding a new consumer needs **no
manual schedule coordination** — the slot is computed and collisions are avoided
by construction. Bands in use:

- `improve-codebase-architecture`: **Mon/Wed/Sat 00–04 UTC**
  (Sun/Tue/Fri evening CT). The per-repo minute/hour is unchanged from the original
  Saturday stagger — only the day-of-week list grew to `1,3,6`. No cron collisions
  across the current estate (verified).
- `staleness-review`: **first Monday 13:xx UTC** (08:xx CT) — hand-chosen, not
  hash-staggered (the hash-stagger covers only the 3×/week loop).

## Cross-repo dependencies

- **Reusable bodies** (both loops): hosted once in skills as `workflow_call`
  reusable workflows (`.github/workflows/*-reusable.yml`). Consumers vendor a
  thin caller stub (cron + `uses:` + `@claude-loops-v1` tag). The skills repo
  uses a local-path `./` ref (canary) ([ADR 0029](../adr/0029-apply-agent-research-joins-the-reusable-body-rail.md)).
- **Harness** (`harness/cli.py` + prompts): fetched fresh each run via
  `git clone --depth 1 https://github.com/dividedby/skills.git` — by both
  reusable bodies (clone form)
  ([ADR 0014](../adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)).
- **arch-review skill + depth rubric:** `mattpocock/skills@main`.
- **Tokens:** own-repo `GITHUB_TOKEN` (minted by `workflow_call` in caller
  context; never passed explicitly); `CLAUDE_CODE_OAUTH_TOKEN` passed explicitly
  through `secrets:` (never `inherit`).
- **Model:** pinned to `claude-sonnet-5` (no floating alias).

## The publish seam (which loops it covers)

The harness `publish` seam (`harness/cli.py publish`, capped by `MAX_PROPOSALS`)
is used by both loops: `improve-codebase-architecture` and `staleness-review`. A
fix to the harness publish seam (e.g.
[ADR 0025](../adr/0025-publish-seam-recovers-malformed-output-loudly-before-failing.md))
reaches both.

## Cost tracking

Each loop emits a `total_cost_usd=…` line via `harness/cli.py digest` (run on
`if: always()`, so cost is captured even on a failed run), readable from the
Actions run log. The cross-repo cost ledger that once scraped it was discontinued
with `agent-research` ([ADR 0038](../adr/0038-retire-knowledge-application-after-agent-research-decommission.md)).
