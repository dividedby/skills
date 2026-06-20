# Vendored Claude-powered Workflows

A reference map of the three vendored **proposal-loop** workflows across the five
repos that run them: cron slots, timing, per-run budget, issue caps, and
cross-repo dependencies. It doubles as the reference surface for
[#365](https://github.com/dividedby/skills/issues/365) (guard envelope drift) and
[#366](https://github.com/dividedby/skills/issues/366) (reusable workflows to
shrink the envelope).

**Snapshot date:** 2026-06-20 — hand-maintained until #365 lands a generator +
`git diff --exit-code` gate. To refresh, re-read
`.github/workflows/{improve-codebase-architecture,apply-agent-research,staleness-review}.yml`
in each repo.

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

Repo roles: **skills** = host (carries the harness in-tree); **agent-research** =
knowledge-base producer; **goodreads-bot** = deployed app (default branch
`staging`); **moodreader**, **tweakcc-maint** = consumers.

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
| moodreader | `50 1 * * 1` | Sun 20:50 | 20m | $3 | 1 |
| goodreads-bot | `7 13 * * 1` | Mon 08:07 | 20m | $3 | 1 |
| skills | `8 13 * * 1` | Mon 08:08 | 20m | $3 | 1 |
| tweakcc-maint | `9 13 * * 1` | Mon 08:09 | 20m | $3 | 1 |
| agent-research | `17 13 * * 1` | Mon 08:17 | 20m | $3 | 1 |

- Gated to the **first Monday** via a `first-monday-gate` step (cron fires every
  Monday; the gate no-ops the other weeks).
- Uses the harness **`publish` seam**; cap = 1.
- **Outlier:** moodreader runs at `50 1 * * 1` (Sun 20:50 CT) — a different hour
  band from the others (13:xx UTC). Verify intent; flag as possible drift (#365).

## Hash-stagger slots

Each cron minute is derived deterministically from `sha1("<repo>/<loop>")` within
a fixed band (agent-research ADR 0022), so onboarding a new consumer needs **no
manual schedule coordination** — the slot is computed and collisions are avoided
by construction. Bands in use:

- `improve-codebase-architecture` + `apply-agent-research`: **Mon/Wed/Sat 00–04 UTC**
  (Sun/Tue/Fri evening CT). The per-repo minute/hour is unchanged from the original
  Saturday stagger — only the day-of-week list grew to `1,3,6`. No cron collisions
  across the current estate (verified).
- `staleness-review`: **first Monday 13:xx UTC** (08:xx CT) — except moodreader
  (see outlier above).

## Cross-repo dependencies

- **Harness** (`harness/cli.py` + prompts): fetched fresh each run via
  `git clone --depth 1 https://github.com/dividedby/skills.git`
  ([ADR 0014](../adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md));
  the skills host uses its in-tree checkout.
- **arch-review skill + depth rubric:** `mattpocock/skills@main`.
- **Knowledge mirror:** `dividedby/agent-research-knowledge@main` (consumers);
  the agent-research producer reads its own `knowledge/` tree.
- **Tokens:** own-repo `GITHUB_TOKEN`; `SKILLS_TRACKER_TOKEN` for cross-repo
  writes.
- **Model:** pinned to `claude-sonnet-4-6` (no floating alias).

## The publish seam (which loops it covers)

The harness `publish` seam (`harness/cli.py publish`, capped by `MAX_PROPOSALS`)
is used by **two** loops: `improve-codebase-architecture` and `staleness-review`.
`apply-agent-research` files through the **skill's own guarded `cli.py`** — a
separate code path. A fix to the harness publish seam (e.g.
[ADR 0025](../adr/0025-publish-seam-recovers-malformed-output-loudly-before-failing.md))
reaches those two loops, not the third.

## Cost tracking

Each loop emits a `total_cost_usd=…` ledger line via `harness/cli.py digest`
(run on `if: always()`, so cost is captured even on a failed run). A cross-repo
cost hub scrapes it — onboarding at `dividedby/agent-research`
`docs/cost-tracking.md`. (Anthropic walked back the `claude -p` SDK credit, so
staying within the credit is no longer a primary concern; tracking is retained in
case it returns.)
