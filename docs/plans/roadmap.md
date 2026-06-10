# skills — Execution Roadmap (source of record)

> **Status:** active · **Owner:** maintainer + agents
>
> The authoritative execution roadmap. Every open issue appears in the master
> census below, and this is the single place to go to pick the next thing to
> work on. **This document self-updates:** every PR that opens, advances, or
> closes an issue updates that issue's row in the same branch — a PreToolUse hook
> (`.claude/hooks/roadmap-guard.py`) enforces it. Out-of-band drift (issues
> changed via `gh`/web between sessions) is caught by a SessionStart nudge
> (`.claude/hooks/roadmap-drift-nudge.py`) and repaired with `/roadmap`.

## How to use this doc (read this as your instructions)

You have been pointed here to work the backlog. This section *is* the prompt —
no other guidance is needed. Follow it top to bottom:

1. **Pick the work.** From the top priority wave, take the earliest row whose
   `Status` is `Next` and whose `Deps` are all satisfied (closed). If the top
   wave has no unblocked `Next`, drop to the next wave. Ties break by row order.
2. **Read the issue in full — body *and* every comment.** Open the linked issue
   (`gh issue view <#> --comments`). The **issue body is authoritative** for
   scope and acceptance criteria; the **comments carry live guidance** —
   unblock notes, routing, and sequencing that `/roadmap` writes back as the
   roadmap reconciles. Do not act on the body alone; a comment may have changed
   the plan. This census row only *routes and orders* — it never restates scope.
3. **Invoke the routed skill.** Use the skill(s) named in the row's `Skill(s)`
   cell as your method; honor the `Notes` cell for any roadmap-only sequencing.
4. **Update this doc's row in your branch before you commit** (the guard hook
   blocks an issue-referencing commit otherwise): set `Status`, and update
   `Deps` on anything your change unblocks.

## Burn-down (2026-06-10)
Reconciled against live `gh` (`/roadmap`). **9 issues — 1 closed (11%), 8 open.**
**Closed (cumulative): 0.** ← integer total of all closed issues ever, including
those whose rows have been pruned from collapsed waves; bumped, never recomputed
from the table (pruned rows are gone), so the count survives wave pruning.

| Bucket | Count | Issues |
|---|---|---|
| **Ready (agent)** — loop-eligible | 0 | — |
| **Ready (human / HITL)**          | 1 | #58 |
| **Blocked / deferred**            | 5 | #75 #98 #112 #125 #153 |
| **Tracking** (epic / PRD parents) | 0 | — |
| **Meta** (idea-inbox / onboarding)| 2 | #91 #220 |

Open by wave: W1 1 · W2 5 · Meta 2 · unscoped 0.

## Priority waves
| Wave | Theme | Issues | Gate to enter |
| ---- | ----- | ------ | ------------- |
| **W1** | Now — roadmap + urgent posture | #216 #58 | none — active now |
| **W2** | Corroboration-gated skill backlog | #75 #98 #112 #125 #153 | a cross-repo +1 lands (ADR 0006); #75 enables the other four |
| **Meta** | Standing intake / cross-cutting | #91 #220 | n/a |

## Master census (active waves inline)
Open waves and the active census stay inline. A **wholly-closed** wave collapses
into a `<details>` (below); once a *newer* wave is active, the collapsed wave's
rows are **pruned** to a one-line summary and the Burn-down cumulative count is
bumped (see Self-update protocol + ADR 0023).

| # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |
| - | ----- | ---- | ------ | ----- | -------- | ---- | ----- |
| 216 | Dogfood the roadmap pattern — bootstrap roadmap into skills itself (ADR 0023) | W1 | **Done** | agent | `/roadmap` | — | bootstrapped & merged (#221) |
| 58 | Decide CI auth/billing posture before the 2026-06-15 Agent SDK credit change (subscription token vs API key) | W1 | **Next** | human | — | — | deadline 2026-06-15 (urgent human decision) |
| 75 | Demonstrate organic cross-repo skill-request +1 across two distinct Consumers | W2 | **Parked** | human | — | — | awaiting-corroboration; enabler for the W2 cluster |
| 98 | Skill request: playbook-driven migration | W2 | **Parked** | loop | `write-a-skill` | #75 | awaiting-corroboration |
| 112 | Skill request: audit a codebase for agent legibility | W2 | **Parked** | loop | `write-a-skill` | #75 | awaiting-corroboration |
| 125 | New engineering skill: prefactor before the easy change | W2 | **Parked** | loop | `write-a-skill` | #75 | source:agent-research; awaiting-corroboration |
| 153 | New engineering skill: agentic release-QA gate | W2 | **Parked** | loop | `write-a-skill` | #75 | awaiting-corroboration |
| 91 | 💡 Idea Inbox | Meta | **Tracking** | human | — | — | 💡 Idea Inbox — standing intake row (ADR 0021) |
| 220 | 🗺️ Roadmap (read-only mirror) | Meta | **Tracking** | machine | — | — | machine-owned CI render of this doc (ADR 0020); render target, not backlog |

## Legend
- **Status** — `Next` (do now) · `Backlog` (ready, unstarted) · `Blocked`
  (waiting on a dep) · `Parked` (deferred/needs-design/wontfix) · `Tracking`
  (epic/PRD parent) · `Done` (closed).
- **Owner** — `agent` · `human` · `mixed`.
- **Deps** — blocking issues; _italic_ = already closed (satisfied).
- **Notes** — roadmap-only sequencing guidance. Scope/AC live in the issue, not here.
- **Closed-wave collapse + prune** — a wholly-closed wave is wrapped in a collapsed
  `<details><summary>Closed wave W# — theme</summary>`; once a *newer* wave is
  active it is **pruned** to a one-line summary and the Burn-down cumulative count
  is bumped. The census is an **execution view** (the active backlog at a glance),
  not the archive — GitHub + git history are the archive (ADR 0023). Open waves and
  the active census never collapse.
- **Closed (cumulative)** — a running integer of all-time closed issues, bumped on
  each prune so the total survives row deletion (it is *not* recomputable from the
  table once rows are pruned).
- **Burn-down buckets** — a projection of the census onto the existing `Owner` +
  `Status` + label vocabulary, recomputed every reconcile (no new data source):
  - **Ready (agent)** — loop-eligible: `ready-for-agent` (agent-owned, `Next`/`Backlog`,
    deps satisfied). Carries a *strong agent brief* (clear module + AC + TDD notes,
    a determinism/offline boundary, report-only where applicable, explicit
    out-of-scope) — the bar to be safely looped; see `/roadmap`'s "Surfacing
    AFK-able work".
  - **Ready (human / HITL)** — `ready-for-human` (human-owned, ready to act).
  - **Blocked / deferred** — `Blocked` or `Parked` with an open dep/hold.
  - **Tracking** — `Tracking` epic/PRD parent rows.
  - **Meta** — idea-inbox / workflow-onboarding rows.

## Self-update protocol
Any PR that opens/advances/closes an issue updates that issue's census row
(minimally `Status`, plus `Deps` on anything it unblocks). Closed → `Status: Done`.
**Closed-wave lifecycle (ADR 0023):** when *every* issue in a wave is `Done`,
collapse that wave's rows into a `<details><summary>Closed wave W# — theme</summary>`;
once a *newer* wave is active, **prune** the collapsed rows to a one-line wave
summary and **bump the Burn-down cumulative closed-count integer** (do not
recompute it from the table — pruned rows are gone). The pruned rows are not lost:
closed issues persist on GitHub and every old row persists in git history. In-branch
freshness enforced by `roadmap-guard.py`; out-of-band
drift (issues changed via `gh`/web between sessions) is *detected* by the
SessionStart `roadmap-drift-nudge.py` and *repaired* by `/roadmap`.
