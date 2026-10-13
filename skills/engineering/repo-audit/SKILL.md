---
name: repo-audit
description: >
  User-invoked audit that hunts high-leverage improvements in a repo and produces a small set of epics with an ordered roadmap — reconciled against the existing backlog, not filed beside it.
disable-model-invocation: true
---

# Repo Audit

A **leverage hunt**, not a coverage exercise. This skill hunts the improvements that matter — deletions, leanness/performance wins, architectural deepening, missing capabilities — and synthesises them into an ordered roadmap of epics, fully reconciled against the repo's existing backlog.

Defers:
- `to-spec`, `to-tickets`, `improve-codebase-architecture` (explore walk, git-log hot-spot idea) — `mattpocock/skills` @ `49dd158d1076134a641b33efb035946536778336`; soft-deps per ADR 0024, expected installed, nothing vendored.
- `tdd` (pointer only) and `/setup-matt-pocock-skills` (when a target repo lacks tracker/label docs).
- [`playbook.md`](./playbook.md) — this skill's per-lens signal catalog and the Stage 1 evidence pack.
- Built-in `Workflow` tool — ADR 0036; ADR 0041 (amendment) for dropping the peer round.

## When to use

- You want to know what the highest-leverage improvements in a repo are.
- The backlog has drifted from the codebase and needs a ground-truth reset, or you're planning a quarter and want an ordered roadmap, not a flat pile of tickets.

## When not to use

- You need just one domain (reach for `tdd`, `improve-codebase-architecture`, etc. directly), the project is too early-stage to audit, or you only need a PR review or a single-file fix.

## Stage 1 — Context, backlog, evidence pack

Runs inline in the main session; no agents.

- **Layout.** Read the repo's Claude config (`.claude/`, `CLAUDE.md` / `AGENTS.md`, hooks) and map its layout: tech stack, CI, test footprint, main modules. Record `git rev-parse --short HEAD` as the audited ref.
- **Backlog.** Pull every open GitHub issue and epic into context now — not later. Keep a compact index (number, title, labels, one-line gist); seats may `gh issue view` for detail. The audit is framed as "what is missing or wrong relative to what is already tracked," which requires the backlog present from the first finding.
- **Standing automation.** Enumerate existing CI and scheduled workflows. Where one already covers ground the hunt would cover, note it so the hunt focuses on what's missing.
- **Evidence pack.** Run the deterministic detectors and the churn hotspot ranking (see `Stage 1 evidence pack` in the playbook). Keep digests, not raw output; log any skipped runner. If `git log` is unavailable (not a git repo, shallow clone), skip the hotspot ranking and log it; never block. Every seat receives the pack.
- **Tracker check.** Does the target repo document its tracker and labels (this repo: `docs/agents/issue-tracker.md`, `docs/agents/labels.md`)? Record the vocabulary Stage 4 will use. If missing, note it: the Stage 3 gate must say so, and Stage 4 does not start until the user chooses (run `/setup-matt-pocock-skills`, or accept the CORE labels).

**Completion criterion:** layout understood, backlog indexed, CI inventory complete, evidence pack built, tracker vocabulary recorded, audited ref recorded.

## Stage 2 — Leverage hunt (blind seats, one synthesis)

Blind seats run through the built-in Workflow tool's `parallel()`; one synthesis agent merges and verifies. At most **6 agents** (up to 5 seats + 1 synthesis). Seats do not see each other's findings. Each seat notes the open issue a finding touches, or that none does — Stage 3 needs it.

### Seat selection

Default is all five. Skip a lens only for a stated reason, and log every skip. Never add seats beyond five.

| Lens | Hunts | Skip when |
|---|---|---|
| **Deletionist** | Dead code, unused deps, orphaned workflows, pass-through abstractions | Repo has no code or config |
| **Performance Analyst** | Hot paths, N+1 work, unnecessary work, scaling risks | No runtime or hot path (e.g. docs-only repo) |
| **Architect** | Explore walk: friction, shallow modules, untestable seams | No module structure to deepen |
| **Capability Scout** | Gaps between what the repo does and what it should do | No stated goals or docs to compare against |
| **Convention & Backlog Keeper** | Convention drift, duplicate or already-done issues | Zero open issues and no documented conventions |

Illustrative lineup log (fictional repo):

```
Panel lineup for: "acme/web-api"
  ✓ Deletionist           — 14 knip hits and top-5 hotspots in src/billing
  ✓ Capability Scout      — README promises webhooks; no handler in the evidence pack
  ✓ Convention & Backlog  — 62 open issues; ADRs and label docs present
  ✗ Performance Analyst   — skipped: no hot path in the evidence pack
```

### Seat brief

Each seat gets: one lens (its playbook section), the evidence pack and backlog index in `args`, read-only tools, and these boundaries — no GitHub mutation, no commentary on other lenses, at most 8 findings, each with a concrete path and observed signal.

Seat output schema (fields): `lens`; `findings[]` of `category` (delete-lean | performance | arch-deepening | missing-capability | convention), `finding`, `evidence{path, signal}`, `open_issue` (number or none), `altitude` (file | batch | drop).

### Synthesis

A separate agent reads all seat outputs, presented in randomized order. It:

1. Reads each finding's cited path and confirms the claim. It drops what it cannot confirm and lists each drop in `dropped[]` with a reason — no silent drops.
2. Merges duplicates by root cause, keeping the strongest evidence and recording the `lenses[]` that surfaced it.
3. Confirms altitude, annotates touched issues, and flags supersession or already-implemented candidates.
4. Adds no new findings.

Output schema: `findings[]` (seat fields plus `lenses[]`, `verified: true`), `dropped[{finding, reason}]`, `touched_issues[]`. This is the only input Stage 3 sees.

### Degradation

Log which tier ran. Evidence verification at the cited path applies in every tier; only blind isolation is lost.

1. **Workflow available** — as above.
2. **Workflow unavailable** (it is stripped from subagents) — one Agent-tool call per lens in parallel, same schema stated in prose; the main session does the synthesis.
3. **No Agent tool either** — a sequential single-pass hunt over the five categories using the playbook.

### Altitude bar

Every finding passes a three-way filter (per seat, confirmed in synthesis) before Stage 3:

- **File** — meaningful impact, justifies its own issue or epic.
- **Batch** — low individual impact; collect into a single "minor cleanups" issue.
- **Drop** — trivial or not worth the cost of tracking.

Nothing below this bar ships as a standalone issue. Err toward Drop over Batch, and Batch over standalone trivia.

### Illustrative sketch

```
// illustrative only — not a runnable script (ADR 0002)
// No Math.random(), Date.now() or argless new Date(): Workflow scripts throw on them.
const { seats, pack, backlog } = args;          // lineup chosen by seat selection
log("lineup: " + seats.map(s => s.name).join(", "));
const results = (await parallel(
  seats.map(s => () =>
    agent(seatPrompt(s, pack, backlog), {
      label: s.name, phase: "hunt", schema: SEAT_SCHEMA, model: "sonnet",
    }))
)).filter(Boolean);                             // a failed seat returns null
return await agent(synthPrompt(results), {      // seats shuffled with a seeded order
  label: "synthesis", phase: "synthesize", schema: MERGED_SCHEMA,
  model: "sonnet", effort: "high",
});
```

Two properties matter: seats are blind to each other, and synthesis is a dedicated agent with an explicit merge-and-verify duty — not the last seat to finish. **Completion criterion:** lineup and skips logged, tier logged, synthesis output schema-valid, `dropped[]` shown to the user.

## Stage 3 — Reconcile, epics, approval gate

Four pass criteria must hold:
- Every touched issue is dispositioned.
- Output is epics plus an ordered roadmap.
- Nothing below the altitude bar ships as a standalone issue.
- No flat-ticket failure.

3a and 3b are read-only proposals in the conversation; nothing is mutated until the approval gate.

### 3a. Reconciliation proposal

For every open issue the findings touch, propose one disposition:
- **Keep** — the issue is correct; link the finding to it.
- **Rewrite** — the issue needs a better problem statement, scope, or priority.
- **Dedup/merge** — the finding and an issue describe the same root cause; fold them.
- **Supersede** — a finding makes the issue obsolete or wrongly scoped; close with a rationale.

Untouched issues on a large backlog get a single bulk "reviewed, no action" line — nothing is silently ignored.

### 3b. Epics + ordered roadmap

Group surviving findings (file-rated, plus the one optional batch) into named epics. Each epic lists its findings, their evidence paths, and the audited ref. Order epics by impact, dependencies, and sequencing constraints.

**Roadmap template:**

```markdown
## Roadmap

### Epic 1 — [Name]
[One-sentence problem statement]
Depends on: —
Unlocks: Epic 2, Epic 3

### Epic 2 — [Name]   (same fields; repeat per epic)
**Sequencing rationale:** [One paragraph explaining why this order — risk, unblocking, dependencies.]
```

### 3c. Altitude check

Confirm nothing below the altitude bar survived as a standalone issue; batch or drop it now.

### 3d. Failure condition

A run that produced only standalone bug tickets — no epics, no roadmap, no reconciliation — has **failed the audit**: go back to Stage 2.

### Approval gate

Present (i) the reconciliation table, with the exact mutation each row implies (rewrite, close, merge — with proposed text or rationale), and (ii) the roadmap. State the label vocabulary Stage 4 will use, and any missing tracker docs. Then **STOP**.

Proceed only on an explicit go-ahead in a later user message. Partial approval means apply only the approved rows. No `gh` write happens before it: issue rewrite, close, merge, create, label edits, `to-spec` and `to-tickets`.

### 3e. Apply

Apply the approved reconciliation, then publish each approved epic with `to-spec`. Epics carry `epic` plus a best-effort `size:*` label and **not** `ready-for-agent` (it grants autonomous implement-and-merge, which is wrong for an aggregate); pass this to `to-spec` explicitly, since it defaults to `ready-for-agent`.

**Completion criterion:** the four pass criteria hold, the approval gate was passed, and only approved mutations were applied.

## Stage 4 — Decompose

Runs only after the approval gate. Invoke `to-tickets` once per published epic with:

- **Source** — the epic issue (number/URL), so every ticket becomes its native sub-issue.
- **Context and tracker** — the epic's findings plus domain vocabulary from `CONTEXT.md` and ADRs; GitHub per the target repo's `docs/agents/issue-tracker.md`.
- **Labels** — the vocabulary from the target repo's `docs/agents/labels.md`, else this repo's CORE set. Children get `ready-for-agent`, or `ready-for-human` where a human judgment gates the work; a ticket blocked only by sibling tickets stays `ready-for-agent` with a native blocking edge (`blocked` is for external dependencies or decisions). Add a category (`enhancement` / `chore` / `bug`) and best-effort `size:S|M|L|XL`.

`to-tickets` runs its own granularity and dependency quiz; roadmap approval does not waive it. Tickets carry no file paths or code snippets (upstream rule) — paths and the audited ref live in the epic body. Epic-to-epic order stays in the roadmap text. If `to-tickets` is not installed, stop and tell the user to install `mattpocock/skills`; do not reimplement it.

## Done checklist

- [ ] Lineup, skips and tier logged; synthesis schema-valid; `dropped[]` shown
- [ ] Every touched issue dispositioned; epics and roadmap present (no flat-ticket failure); nothing below the altitude bar shipped standalone
- [ ] Approval received before the first GitHub write (message referenced)
- [ ] Every epic has at least one child ticket, a native sub-issue carrying correct labels
- [ ] Blocking edges are native links; audited ref recorded on each epic

## Leverage-hunt catalog

See [`playbook.md`](./playbook.md) for the Stage 1 evidence pack and, per lens, what to look for — signals, patterns, and optional-input protocols.
