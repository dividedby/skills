<!-- agent-protocol: reconcile=/roadmap; drain=docs/agents/idea-inbox.md -->
# skills — Execution Roadmap (source of record)

> **Read-only mirror.** This is the human-facing execution roadmap: the master
> census below is the single place to go to pick the next thing to work on. The
> doc self-updates in-branch and is mirrored read-only to a pinned issue — edit
> the working-tree doc, not the mirror. Agent operating instructions are **not**
> in this body: reconcile lives in the `roadmap` skill (`/roadmap`), inbox drain
> in `docs/agents/idea-inbox.md` (see the breadcrumb at the top of the raw doc).

## Burn-down (2026-06-11)
**17 issues — 8 closed (47%), 9 open.** Closed (cumulative): 0. Open by wave: W1 1 · W3 1 · W2 5 · Meta 2 · unscoped 0.

| Bucket | Count | Issues |
|---|---|---|
| **Ready (agent)** — loop-eligible | 0 | — |
| **Ready (human / HITL)**          | 1 | #58 |
| **Blocked / deferred**            | 5 | #75 #98 #112 #125 #153 |
| **Tracking** (epic / PRD parents) | 1 | #225 |
| **Meta** (idea-inbox / onboarding)| 2 | #91 #220 |

## Priority waves
| Wave | Theme | Issues | Gate to enter |
| ---- | ----- | ------ | ------------- |
| **W1** | Now — roadmap + urgent posture | #216 #58 | none — active now |
| **W3** | Idea Inbox/Roadmap thinning (progressive-disclosure body split) | #225 #226 #227 #228 #229 #230 #231 | none — active now; #226 (ADRs) unblocks the layout slices |
| **W2** | Corroboration-gated skill backlog | #75 #98 #112 #125 #153 | a cross-repo +1 lands (ADR 0006); #75 enables the other four |
| **Meta** | Standing intake / cross-cutting | #91 #220 #239 | n/a |

## Census
Open waves stay inline, ordered by wave priority (`W1` first). A **wholly-closed**
wave collapses into a `<details>`; once a *newer* wave is active, the collapsed
wave's rows are **pruned** to a one-line summary and the Burn-down cumulative count
is bumped (see Legend; ADR 0023).

| # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |
| - | ----- | ---- | ------ | ----- | -------- | ---- | ----- |
| 216 | Dogfood the roadmap pattern — bootstrap roadmap into skills itself (ADR 0023) | W1 | **Done** | agent | `/roadmap` | — | bootstrapped & merged (#221) |
| 58 | Decide CI auth/billing posture before the 2026-06-15 Agent SDK credit change (subscription token vs API key) | W1 | **Next** | human | — | — | deadline 2026-06-15 (urgent human decision) |
| 225 | PRD: Thin the Idea Inbox + Roadmap (progressive-disclosure body split) | W3 | **Tracking** | mixed | `/to-prd` | — | epic/PRD parent for the thinning slices #226–#231 |
| 226 | ADRs: migration auto-merge carve-out + progressive-disclosure body split + thin-pointer census cell | W3 | **Done** | mixed | `grill-with-docs` | — | merged via PR #232 (ADRs 0022 amend + 0024 + 0025) |
| 227 | Guard: enforce census cell-cap + Burn-down/census consistency | W3 | **Done** | agent | `/tdd` | — | guard now enforces cell-cap + Burn-down consistency; unblocks #231 |
| 228 | Roadmap canonical layout: thin human body + breadcrumb + Burn-down recompute | W3 | **Done** | agent | `write-a-skill` | _#226_ | thin template body + breadcrumb schema in SKILL.md |
| 229 | Inbox canonical layout: single-source drain doc + thin template + breadcrumb | W3 | **Done** | agent | `write-a-skill` | _#226_ | drain doc + thin template + breadcrumb landed |
| 230 | /roadmap migrate route: restructure the intake pair in one human-reviewed PR | W3 | **Done** | agent | `write-a-skill` | _#226_ _#228_ _#229_ | migrate-intake-pair route added to SKILL.md; consumer rollout out of scope |
| 231 | Pilot: migrate the skills repo's own Idea Inbox #91 + Roadmap #220 | W3 | **Done** | mixed | `/roadmap` | _#227_ _#228_ _#229_ _#230_ | HITL pilot migration; thinned this doc + proposed #91 body; #220 re-renders via CI |
| 75 | Demonstrate organic cross-repo skill-request +1 across two distinct Consumers | W2 | **Parked** | human | — | — | awaiting-corroboration; enabler for the W2 cluster |
| 98 | Skill request: playbook-driven migration | W2 | **Parked** | loop | `write-a-skill` | #75 | awaiting-corroboration |
| 112 | Skill request: audit a codebase for agent legibility | W2 | **Parked** | loop | `write-a-skill` | #75 | awaiting-corroboration |
| 125 | New engineering skill: prefactor before the easy change | W2 | **Parked** | loop | `write-a-skill` | #75 | source:agent-research; awaiting-corroboration |
| 153 | New engineering skill: agentic release-QA gate | W2 | **Parked** | loop | `write-a-skill` | #75 | awaiting-corroboration |
| 91 | 💡 Idea Inbox | Meta | **Tracking** | human | — | — | 💡 Idea Inbox — standing intake row (ADR 0021) |
| 220 | 🗺️ Roadmap (read-only mirror) | Meta | **Tracking** | machine | — | — | machine-owned CI render of this doc (ADR 0020); render target, not backlog |
| 239 | /roadmap reconcile: derive closed-state from census + open set instead of bulk-loading --state all | Meta | **Done** | agent | `/roadmap` | — | hook + SKILL.md now fetch `--state open` and set-difference closed-ness |

## Legend
- **Wave** — priority ordering; the census is read top wave (`W1`) first, then
  down. Themes and entry gates are in the Priority waves table above; the `—` /
  `Meta` pseudo-waves hold cross-cutting and standing rows.
- **Status** — `Next` (do now) · `Backlog` (ready, unstarted) · `Blocked`
  (waiting on a dep) · `Parked` (deferred/needs-design/wontfix) · `Tracking`
  (epic/PRD parent) · `Done` (closed). A single token from this set; deep context
  lives on the linked issue, not the cell (ADR 0025).
- **Owner** — `agent` · `human` · `mixed` · `machine` · `loop`.
- **Skill(s)** — the routed skill an agent invokes as its method for the row.
- **Deps** — blocking issues; _italic_ = already closed (satisfied).
- **Notes** — one-line roadmap-only sequencing guidance (≤120 chars, single
  line; ADR 0025). Scope/AC live in the issue, not here.
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
