<!-- agent-protocol: reconcile=/roadmap; drain=docs/agents/idea-inbox.md -->
# <project> — Execution Roadmap (source of record)

> **Read-only mirror.** This is the human-facing execution roadmap: the master
> census below is the single place to go to pick the next thing to work on. The
> doc self-updates in-branch and is mirrored read-only to a pinned issue — edit
> the working-tree doc, not the mirror. Agent operating instructions are **not**
> in this body: reconcile lives in the `roadmap` skill (`/roadmap`), inbox drain
> in `docs/agents/idea-inbox.md` (see the breadcrumb at the top of the raw doc).

## Burn-down (<date>)
**<total> issues — <closed> closed (<pct>%), <open> open.** Closed (cumulative): <N>. Open by wave: W1 n · … · unscoped n.

| Bucket | Count | Issues |
|---|---|---|
| **Ready (agent)** — loop-eligible | N | #… |
| **Ready (human / HITL)**          | N | #… |
| **Blocked / deferred**            | N | #… |
| **Tracking** (epic / PRD parents) | N | #… |
| **Meta** (idea-inbox / onboarding)| N | #… |

## Census
Open waves stay inline, ordered by wave priority (`W1` first). A **wholly-closed**
wave collapses into a `<details>`; once a *newer* wave is active, the collapsed
wave's rows are **pruned** to a one-line summary and the Burn-down cumulative count
is bumped (see Legend; ADR 0023).

| # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |
| - | ----- | ---- | ------ | ----- | -------- | ---- | ----- |
| NN | <short title> | W1 | **Next** | agent | `/tdd` | — | — |

<details>
<summary>Closed wave W0 — &lt;theme&gt; (closed; superseded by W1)</summary>

W0 shipped <one-line summary of what the wave delivered>. Rows pruned — closed
issues live on GitHub + in git history; the cumulative count above carries the
total. (Until a newer wave is active, a freshly-closed wave keeps its rows inside
this `<details>` instead of the summary line.)

</details>

## Legend
- **Wave** — priority ordering; the census is read top wave (`W1`) first, then
  down. A wave row carries its theme and gate inline (e.g. `W1 — Now (gate: none)`);
  the `—` / `Meta` pseudo-waves hold cross-cutting and standing rows.
- **Status** — `Next` (do now) · `Backlog` (ready, unstarted) · `Blocked`
  (waiting on a dep) · `Parked` (deferred/needs-design/wontfix) · `Tracking`
  (epic/PRD parent) · `Done` (closed). A single token from this set; deep context
  lives on the linked issue, not the cell (ADR 0025).
- **Owner** — `agent` · `human` · `mixed` · `machine` · `loop`.
- **Skill(s)** — the routed skill an agent invokes as its method for the row.
- **Deps** — blocking issues; _italic_ = already closed (satisfied).
- **Notes** — one-line roadmap-only sequencing guidance (≤120 chars, single
  token/line; ADR 0025). Scope/AC live in the issue, not here.
- **Cells are thin pointers (ADR 0025).** Notes/Status cells are a single line
  capped at ~120 chars and Status is a single Legend token; the linked issue holds
  the narrative. `roadmap-guard` denies an over-cap or multi-line cell in-branch.
- **Closed-wave collapse + prune (ADR 0023).** A wholly-closed wave is wrapped in a
  collapsed `<details><summary>Closed wave W# — theme</summary>`; once a *newer*
  wave is active it is **pruned** to a one-line summary and the Burn-down cumulative
  count is bumped. The census is an **execution view** (the active backlog at a
  glance), not the archive — GitHub + git history are the archive. Open waves and
  the active census never collapse.
- **Closed (cumulative)** — a running integer of all-time closed issues, bumped on
  each prune so the total survives row deletion (it is *not* recomputable from the
  table once rows are pruned).
- **Burn-down buckets** — a projection of the census onto the `Owner` + `Status` +
  label vocabulary, recomputed from the census every reconcile (no new data source):
  - **Ready (agent)** — loop-eligible: `ready-for-agent` (agent-owned, `Next`/`Backlog`,
    deps satisfied). Carries a *strong agent brief* (clear module + AC + TDD notes,
    a determinism/offline boundary, report-only where applicable, explicit
    out-of-scope) — the bar to be safely looped; see `/roadmap`'s "Surfacing
    AFK-able work".
  - **Ready (human / HITL)** — `ready-for-human` (human-owned, ready to act).
  - **Blocked / deferred** — `Blocked` or `Parked` with an open dep/hold.
  - **Tracking** — `Tracking` epic/PRD parent rows.
  - **Meta** — idea-inbox / workflow-onboarding rows.
