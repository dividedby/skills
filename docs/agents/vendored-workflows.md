# Vendored Claude-powered Workflows

A reference map of the three **proposal-loop** workflows across the five repos
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
| `apply-agent-research` | Thin caller stub (cron + `uses:` + tag + `permissions` grant) | `workflow_call` reusable body (`-reusable.yml`) |

Consumers pin the reusable bodies at tag `@claude-loops-v1`. The skills repo
uses a local-path `./` ref (canary — always runs the latest body).
`apply-agent-research` joined the reusable-body rail in ADR 0029: the three
"modes" (host/consumer/producer) are env-wiring, not body forks — one body with
two conditional points serves all three.

**Caller stubs must grant `permissions: { contents: read, issues: write }`** on
the calling job. A called workflow can't be granted more token scope than the
caller holds, and every repo's default workflow permission is read-only — without
the grant the body's `issues: write` exceeds the caller's token and the run
**startup-fails**. The reusable body also declares the same `permissions`; the
two must agree.

**Snapshot date:** 2026-06-20 — live divergence check landed via
[`check-workflow-drift.yml`](../../.github/workflows/check-workflow-drift.yml)
(#365, weekly Sun 04:00 UTC, central in skills). The scheduled job reads each
consumer repo's vendored files via the GitHub Contents API, checks structural
anchors (anchor-presence, not full normalization), and opens a `workflow-drift`
issue in dividedby/skills for any drifted repo. To refresh this table, re-read
`.github/workflows/{improve-codebase-architecture,apply-agent-research,staleness-review}.yml`
in each repo.

**Label-doc drift check** — companion detector landed via
[`check-label-drift.yml`](../../.github/workflows/check-label-drift.yml)
(#415, weekly Sun 05:00 UTC — staggered 1h after workflow-drift). Reads each
consumer's `docs/agents/triage-labels.md` and `docs/agents/labels.md` via the
GitHub Contents API; classifies one of four drift shapes per repo; opens a
`label-drift` issue in dividedby/skills naming `setup-dividedby-skills` as the
fixer. Report-only — never mutates a consumer repo. Requires the same
`ISSUES_TOKEN` secret (with `DRIFT_CHECK_TOKEN` as Option-B fallback) as workflow-drift.

**Idea-inbox drift check** — companion detector landed via
[`check-idea-inbox-drift.yml`](../../.github/workflows/check-idea-inbox-drift.yml)
(#488, weekly Sun 06:00 UTC — staggered 1h after label-drift). Reads each carrier
repo's `docs/agents/idea-inbox.md` via the GitHub Contents API; checks eight
canonical structural anchors (breadcrumb, six drain steps, rolling-window section);
opens an `idea-inbox-drift` issue in dividedby/skills naming `setup-dividedby-skills`
as the fixer; references #489 for the one-time bulk reconciliation of existing drift.
Report-only — never mutates a carrier repo. Requires the same `ISSUES_TOKEN` secret
as workflow-drift and label-drift.

**Reading the crons:** schedules are UTC (authoritative). **CT** is shown for CDT
(Mar–Nov, UTC−5); **subtract 1h in CST** (Nov–Mar). Day codes: `* * 6` =
Saturday, `* * 1` = Monday, `* * 3` = Wednesday. Rows are ordered by UTC time within each table.

## Presence matrix

All five repos run all three loops.

| Loop | skills | moodreader | agent-research | goodreads-bot | tweakcc-maint |
|---|:--:|:--:|:--:|:--:|:--:|
| `improve-codebase-architecture` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `apply-agent-research` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `staleness-review` | ✓ | ✓ | ✓ | ✓ | ✓ |

Repo roles: **skills** = host (carries the harness in-tree and the reusable
`workflow_call` bodies); **agent-research** = knowledge-base producer;
**goodreads-bot** = deployed app (default branch `staging`); **moodreader**,
**tweakcc-maint** = consumers.

## `improve-codebase-architecture` — Mon/Wed/Sat (3×/week)

| Repo | cron (UTC) | CT (CDT) | timeout | budget | issues/run |
|---|---|---|---|---|---|
| moodreader | `3 0 * * 1,3,6` | Sun/Tue/Fri 19:03 | 20m | $3 | 2 |
| skills | `5 0 * * 1,3,6` | Sun/Tue/Fri 19:05 | 20m | $3 | 2 |
| tweakcc-maint | `34 1 * * 1,3,6` | Sun/Tue/Fri 20:34 | 20m | $3 | 2 |
| agent-research | `4 3 * * 1,3,6` | Sun/Tue/Fri 22:04 | 20m | $3 | 2 |
| goodreads-bot | `11 3 * * 1,3,6` | Sun/Tue/Fri 22:11 | 20m | $3 | 2 |

- **Issue cap:** flat cap of 2 estate-wide, no per-repo override, propagates via the fetched-fresh harness. Reference [ADR 0019](../adr/0019-proposal-loops-file-a-budgeted-ranked-top-k.md) (as amended 2026-06-20).
- Uses the harness **`publish` seam** (cap = `MAX_PROPOSALS`, [ADR 0019](../adr/0019-proposal-loops-file-a-budgeted-ranked-top-k.md)).
- Depth rubric fetched fresh from `mattpocock/skills@main`
  ([ADR 0020](../adr/0020-arch-review-fetches-depth-rubric-fresh-and-adds-simplification-legibility-lenses.md)).
- Proposal bodies include a **Design-tension section** — 2–3 candidate-specific
  competing constraints, a sketch under each, and a tension statement — as
  competing-constraint decision-support for the human triaging before implementation
  (ADR 0020, second amendment; async adaptation of DESIGN-IT-TWICE).

## `apply-agent-research` — Mon/Wed/Sat (3×/week)

| Repo | cron (UTC) | CT (CDT) | timeout | budget | issues/run |
|---|---|---|---|---|---|
| moodreader | `39 0 * * 1,3,6` | Sun/Tue/Fri 19:39 | 20m | $3 | 2 |
| skills | `19 1 * * 1,3,6` | Sun/Tue/Fri 20:19 | 20m | $3 | 2 |
| goodreads-bot | `45 1 * * 1,3,6` | Sun/Tue/Fri 20:45 | 20m | $3 | 2 |
| tweakcc-maint | `27 3 * * 1,3,6` | Sun/Tue/Fri 22:27 | 20m | $3 | 2 |
| agent-research | `37 3 * * 1,3,6` | Sun/Tue/Fri 22:37 | 20m job / 15m run | **$15** | 2 |

- **agent-research is the producer**, not a consumer: higher budget ($15),
  shorter run-step timeout (15m), and it reads its **native `knowledge/` corpus**
  rather than cloning the mirror.
- Consumers clone the knowledge mirror `dividedby/agent-research-knowledge@main`.
- Files through the **skill's own guarded `cli.py`** (`gate` / `sanitize` /
  `file`), **not** the harness `publish` seam.

## `staleness-review` — first Monday of the month

| Repo | cron (UTC) | CT (CDT) | timeout | budget | issues/run |
|---|---|---|---|---|---|
| goodreads-bot | `7 13 * * 1` | Mon 08:07 | 20m | $3 | 1 |
| skills | `8 13 * * 1` | Mon 08:08 | 20m | $3 | 1 |
| tweakcc-maint | `9 13 * * 1` | Mon 08:09 | 20m | $3 | 1 |
| moodreader | `10 13 * * 1` | Mon 08:10 | 20m | $3 | 1 |
| agent-research | `17 13 * * 1` | Mon 08:17 | 20m | $3 | 1 |

- Gated to the **first Monday** via a `first-monday-gate` step (cron fires every
  Monday; the gate no-ops the other weeks).
- Uses the harness **`publish` seam**; cap = 1.
- Slots are **hand-chosen** in the 13:xx UTC band (this loop is not hash-staggered;
  ADR 0022 staggers only the two 3×/week loops). moodreader was realigned from an
  off-band `50 1` (Sun 20:50 CT) to `10 13` on 2026-06-20.

## Hash-stagger slots

Each cron minute is derived deterministically from `sha1("<repo>/<loop>")` within
a fixed band (agent-research ADR 0022), so onboarding a new consumer needs **no
manual schedule coordination** — the slot is computed and collisions are avoided
by construction. Bands in use:

- `improve-codebase-architecture` + `apply-agent-research`: **Mon/Wed/Sat 00–04 UTC**
  (Sun/Tue/Fri evening CT). The per-repo minute/hour is unchanged from the original
  Saturday stagger — only the day-of-week list grew to `1,3,6`. No cron collisions
  across the current estate (verified).
- `staleness-review`: **first Monday 13:xx UTC** (08:xx CT) — hand-chosen, not
  hash-staggered (ADR 0022 covers only the two 3×/week loops).

## Cross-repo dependencies

- **Reusable bodies** (all three loops): hosted once in skills as `workflow_call`
  reusable workflows (`.github/workflows/*-reusable.yml`). Consumers vendor a
  thin caller stub (cron + `uses:` + `@claude-loops-v1` tag). The skills repo
  uses a local-path `./` ref (canary). `apply-agent-research` joined the rail in
  ADR 0029.
- **Harness** (`harness/cli.py` + prompts): fetched fresh each run via
  `git clone --depth 1 https://github.com/dividedby/skills.git` — by all three
  reusable bodies (clone form)
  ([ADR 0014](../adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)).
- **arch-review skill + depth rubric:** `mattpocock/skills@main`.
- **Knowledge mirror:** `dividedby/agent-research-knowledge@main` (consumers);
  the agent-research producer reads its own `knowledge/` tree.
- **Tokens:** own-repo `GITHUB_TOKEN` (minted by `workflow_call` in caller
  context; never passed explicitly); `CLAUDE_CODE_OAUTH_TOKEN` passed explicitly
  through `secrets:` (never `inherit`).
- **Model:** pinned to `claude-sonnet-4-6` (no floating alias).

## The publish seam (which loops it covers)

The harness `publish` seam (`harness/cli.py publish`, capped by `MAX_PROPOSALS`)
is used by **two** loops: `improve-codebase-architecture` and `staleness-review`.
`apply-agent-research` files through the **skill's own guarded `cli.py`**
(`skills/meta/apply-agent-research/lib/cli.py`) — a separate code path — even
though its reusable body fetches the harness fresh for the `digest` step. A fix
to the harness publish seam (e.g.
[ADR 0025](../adr/0025-publish-seam-recovers-malformed-output-loudly-before-failing.md))
reaches those two loops, not the third.

## Cost tracking

Each loop emits a `total_cost_usd=…` ledger line via `harness/cli.py digest`
(run on `if: always()`, so cost is captured even on a failed run). A cross-repo
cost hub scrapes it — onboarding at `dividedby/agent-research`
`docs/cost-tracking.md`. (Anthropic walked back the `claude -p` SDK credit, so
staying within the credit is no longer a primary concern; tracking is retained in
case it returns.)
