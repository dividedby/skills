---
name: repo-audit
description: User-invoked audit that hunts high-leverage improvements in a repo and produces a small set of epics with an ordered roadmap — reconciled against the existing backlog, not filed beside it.
disable-model-invocation: true
---

# Repo Audit

A **leverage hunt**, not a coverage exercise. This skill hunts the improvements that matter — deletions, leanness/performance wins, architectural deepening, missing capabilities — and synthesises them into an ordered roadmap of epics, fully reconciled against the repo's existing backlog.

## When to use

- You want to know what the highest-leverage improvements in a repo are.
- The backlog has drifted from the codebase and needs a ground-truth reset.
- You're about to plan a significant quarter and want an ordered roadmap, not a flat pile of tickets.

## When not to use

- You need just one domain: reach for `staleness-audit`, `tdd`, `improve-codebase-architecture`, etc. directly.
- The project is too early-stage to audit (no code yet, prototype only).
- You only need a quick PR review or a single-file fix.

---

## Stage 1 — Context + backlog load

Read the repo's Claude config (`.claude/`, `CLAUDE.md` / `AGENTS.md`, hooks) and map its layout: tech stack, CI, test footprint, main modules. Pull every open GitHub issue and epic into context now — not later. The audit is framed as "what is missing or wrong relative to what is already tracked," and that framing requires the backlog to be present from the first finding.

**Standing-automation inventory.** Enumerate existing CI and scheduled workflows. Where a workflow already covers ground the leverage hunt would cover, note it so the hunt focuses on what's missing.

**Completion criterion:** repo layout understood, open issues loaded, CI inventory complete.

---

## Stage 2 — Leverage hunt

Hunt across four categories. For each finding, immediately note which open issue it touches (or that none does) — you will need this in Stage 3.

### Delete / lean

Look for code, workflows, dependencies, and features that can be deleted outright or radically simplified without hurting users. The best finding here is a deletion that makes everything else easier.

**Optional inputs that feed this category:**
- Staleness scan (dead code, orphaned workflows, stale deps) — run where the repo looks large or long-lived.
- Prior-art check — run where the repo may be reimplementing something that already exists.

### Performance

Look for obvious hot paths, N+1 queries, unnecessary work, and scaling risks visible from architecture and code patterns. Flag where measurement is needed before optimising.

### Architectural deepening

Walk the codebase using the Explore method from `improve-codebase-architecture`: move organically through the code, noting where you experience friction — concepts that require bouncing between many small modules, interfaces nearly as complex as their implementations, logic scattered across callers with no locality, untestable seams. Apply the **deletion test** to anything that looks shallow.

Use `codebase-design` vocabulary throughout: **module**, **interface**, **depth**, **seam**, **adapter**, **leverage**, **locality**. A finding here must name the module(s) involved and describe the deepening opportunity in these terms. For a full architectural deep-dive a maintainer can run separately, see `improve-codebase-architecture` (user-invoked, produces an HTML report).

**Optional inputs:**
- Security check — run where the repo handles auth, user data, or external APIs.
- Test coverage scan — run where coverage appears thin or test strategy is unclear.

### Missing features / capabilities

Look for gaps between what the repo currently does and what it clearly should do given its purpose — missing user journeys, absent error handling, undocumented failure modes.

**Optional inputs:**
- Frontend/UX review — run for repos with meaningful UI surface.
- Docs review — run where docs appear stale, missing, or inconsistent with code.

### Altitude bar

Every finding passes through a three-way filter before it survives to Stage 3:

- **File** — meaningful impact, justifies its own issue or epic. Architectural deepening, significant deletions, performance wins, real capability gaps.
- **Batch** — low individual impact but worth tracking; collect into a single "minor cleanups" issue or fold into an existing one.
- **Drop** — trivial or not worth the cost of tracking. Drop it, don't file it.

Nothing below this bar ships as a standalone issue. Trivia gets one "minor cleanups" batch at most, or is dropped.

**Completion criterion:** findings across all four categories collected; each assigned file / batch / drop; every finding annotated with which open issue it touches (or none).

---

## Stage 3 — Synthesis + integration (hard gate)

This stage has four falsifiable pass criteria. The skill does not complete until all four hold.

### 3a. Reconcile against existing issues

For every open issue the findings touch:
- **Keep** — the existing issue is correct; link the finding to it.
- **Rewrite** — the existing issue needs a better problem statement, scope, or priority; update it.
- **Dedup/merge** — the finding and an existing issue describe the same root cause; fold them.
- **Supersede** — a finding makes an existing issue obsolete or wrongly scoped; close it with a rationale.

Untouched issues on a large backlog get a single bulk "reviewed, no action" acknowledgement — nothing is silently ignored.

### 3b. Group into epics + ordered roadmap

Group surviving findings (file-rated, plus the one optional batch) into named epics. Then produce a roadmap ordering the epics by impact, dependencies, and sequencing constraints. Use `to-prd` to produce per-epic PRDs.

**Roadmap template** (inline — the one artifact `repo-audit` uniquely owns):

```markdown
## Roadmap

### Epic 1 — [Name]
[One-sentence problem statement]
Depends on: —
Unlocks: Epic 2, Epic 3

### Epic 2 — [Name]
[One-sentence problem statement]
Depends on: Epic 1
Unlocks: Epic 4

### Epic 3 — [Name]
[One-sentence problem statement]
Depends on: Epic 1
Unlocks: —

...

**Sequencing rationale:** [One paragraph explaining why this order — risk, unblocking, dependencies.]
```

### 3c. Altitude check

Confirm nothing below the altitude bar survived as a standalone issue. If it did, batch it or drop it now.

### 3d. Failure condition

A run that produced only standalone bug tickets — no epics, no roadmap, no reconciliation against existing issues — has **failed the audit**. This is not "done with warnings." If you reach the end of Stage 3 and the output is a flat pile of tickets, go back to Stage 2.

**Completion criterion:** all four gate criteria satisfied — every touched issue dispositioned, output is epics + ordered roadmap, nothing below altitude bar ships standalone, no flat-ticket failure.

---

## Stage 4 — Decompose epics into issues

Use `to-issues` to decompose each surviving epic into `ready-for-agent` issues with explicit dependency chains. Each issue gets: user story or task description, links to relevant files/PRDs, constraints, and HITL tasks where human judgment is required.

**Completion criterion:** every epic has at least one decomposed `ready-for-agent` issue; no issue is an orphan (each links to its parent epic).

---

## Stage 5 — Self-check

Verify the hard gate held. This is not a five-role review — it is a gate verification:

1. Every existing open issue the audit touched is explicitly dispositioned in the Stage 3 output.
2. The output contains at least one epic and a roadmap. If it does not, the audit has failed — revisit Stage 3.
3. No issue below the altitude bar shipped as a standalone ticket.
4. Every decomposed issue has a state label (`ready-for-agent`, `blocked`, or `ready-for-human`) and the comment that label requires.

**Completion criterion:** all four checks pass, or failing ones are fixed and re-verified before declaring done.

---

## Leverage-hunt catalog

See [`playbook.md`](./playbook.md) for what to look for under each leverage category — specific signals, patterns, and optional-input protocols.
