---
name: repo-audit
description: >
  User-invoked audit that hunts high-leverage improvements in a repo and produces a small set of epics with an ordered roadmap — reconciled against the existing backlog, not filed beside it.
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

## Stage 2 — Leverage hunt (blind panel fan-out)

Stage 2 is structured as a blind multi-persona panel that runs via the built-in
Workflow tool's `parallel()` primitive — the same mechanism `/council` uses for
adversarial diversity. Five personas, each with a distinct evaluative lens, hunt
the codebase independently and cannot see each other's findings during their
sweep. A cross-review round deduplicates and ranks before synthesis. The
synthesised panel output feeds Stage 3 unchanged — the reconcile-against-backlog
hard gate and altitude bar remain exactly as before.

For each finding, the persona responsible notes which open issue it touches (or
that none does). Stage 3 will need this annotation.

### Pre-flight — log the panel lineup

Before any persona runs, log the five-seat lineup and a one-line rationale for
each seat (why this lens, calibrated against the Stage 1 context — what the repo
is, how large it is, what its CI/test footprint looks like). No silent selection.
This mirrors the Step 0 selector log in `/council`.

Illustrative lineup log:

```
Panel lineup for: "dividedby/skills"
  ✓ Deletionist            — large, long-lived repo; deletion is highest-leverage first move
  ✓ Performance Analyst    — harness/ Python + Actions matrix; hot-path and N+1 risks to check
  ✓ Architect              — ~12 skills, shared harness; seam and depth findings likely
  ✓ Capability Scout       — mission-driven repo (skills catalog); gap between stated goals and wiring
  ✓ Convention & Backlog   — strong conventions (ADRs, labels, changelog); open-issue set loaded in Stage 1
```

### Round 1 — Blind parallel sweep

Each persona runs independently via `parallel()`. Personas do **not** see each
other's output during Round 1. Every seat receives the same Stage-1 context
(repo layout, tech stack, CI inventory, open issues) and its own lens; nothing
else.

**Five-seat roster:**

| Persona | Lens | Maps to |
|---|---|---|
| **Deletionist** | Dead code, orphaned workflows, unused deps, pass-through abstractions — the deletion test applied everywhere | Delete / lean |
| **Performance Analyst** | Hot paths, N+1 queries, unnecessary work, scaling risks visible from architecture | Performance |
| **Architect** | Explore walk (from `improve-codebase-architecture`): friction, shallow modules, untestable seams, interface/implementation symmetry; `codebase-design` vocabulary throughout | Architectural deepening |
| **Capability Scout** | Gaps between what the repo does and what it clearly should do — missing journeys, absent error handling, undocumented failure modes | Missing features / capabilities |
| **Convention & Backlog Keeper** | Convention drift (ADRs, labels, changelog, config), naming/structural inconsistencies, and which open issues the other lenses would touch or supersede — grounded against the Stage 1 open-issue set | Cross-cutting; convention and reconciliation signal for Stage 3 |

Each seat returns a structured response:

```
persona: <name>
findings:
  - category: <delete-lean | performance | arch-deepening | missing-capability | convention>
    finding: <one concrete finding>
    evidence: <specific — file, pattern, or signal observed>
    open-issue: <issue number or "none">
    altitude: <file | batch | drop>
```

Optional inputs that personas may draw on (same as the prior sequential hunt):
- Deletionist: staleness scan, prior-art check, deterministic detectors (see playbook)
- Architect: security check (auth/user-data/external-API repos), test coverage scan
- Capability Scout: frontend/UX review, docs review

### Round 2 — Anonymized cross-review / dedup

Seat responses are anonymized (persona labels stripped) and redistributed. Each
persona reads the full set and:

1. Flags duplicates — two or more findings describing the same root cause; names
   the one to keep and why.
2. Ranks the three strongest findings across all seats (not its own).
3. Surfaces any gap the first round missed.

This round produces a **deduplicated ranked finding map** — not a new set of
verdicts. Duplicates are collapsed; surviving findings are annotated with their
cross-seat rank.

### Synthesis — merge into Stage 3 input

> **Temporary — revert on/after 2026-07-07 (Fable 5 sunset).** The synthesis agent runs on **Fable 5** for a trial. Revert: every `fable` in this file → `sonnet`.

A synthesis pass (fable, higher effort — reads all Round 1 responses de-anonymized
plus the Round 2 dedup map) produces the Stage 3 input:

- One unified finding list, duplicates resolved, altitude ratings confirmed.
- Per-finding annotation: category, altitude (file / batch / drop), and which
  open issue it touches.
- A brief panel-diversity note — what the multi-lens sweep surfaced that a
  single sequential pass would likely have missed.

This is the only output Stage 3 sees. The Stage 3 contract (reconcile against
backlog, group into epics, ordered roadmap, altitude check, failure condition) is
unchanged.

### Graceful degradation — Workflow tool unavailable

If the Workflow tool is unavailable or invocation fails, fall back to the prior
sequential hunt: hunt across the four categories (Delete/lean, Performance,
Architectural deepening, Missing features/capabilities) in a single pass, using
the playbook for each. Note the degradation and proceed. The audit still
completes; the blind-isolation and cross-review discipline is skipped, not the
findings.

### Altitude bar

Every finding passes through the three-way filter (applied per persona in Round
1, confirmed in synthesis) before it reaches Stage 3:

- **File** — meaningful impact, justifies its own issue or epic.
- **Batch** — low individual impact; collect into a single "minor cleanups" issue.
- **Drop** — trivial or not worth the cost of tracking.

Nothing below this bar ships as a standalone issue. Trivia gets one "minor
cleanups" batch at most, or is dropped.

**Completion criterion:** panel lineup logged; all five personas ran blind in
Round 1; Round 2 dedup map produced; synthesis merged findings into the Stage 3
input; each finding annotated with category, altitude, and open-issue reference.

### Illustrative Workflow sketch

The sketch below shows the orchestration shape, not a literal script (ADR 0002).
This skill drives the same `/council` Workflow primitive — see ADR 0036.

```
// ponytail: illustrative only — not a runnable literal script (ADR 0002)

const ctx    = stage1Context;   // repo layout, open issues, CI inventory
const lineup = logLineup(ctx);  // pre-flight: log five seats + rationale

// Round 1: each persona hunts blind in parallel
const round1 = await parallel(
  lineup.seats.map(seat =>
    agent(seat.persona, { model: "sonnet", input: { ctx, lens: seat.lens } })
  )
);

// Round 2: anonymized cross-review / dedup
const anonymized = stripPersonaLabels(round1);
const round2 = await parallel(
  lineup.seats.map(seat =>
    agent(seat.persona + "-review", { model: "sonnet", input: anonymized })
  )
);

// Synthesis: merge into Stage 3 input
const stage3Input = await agent("synthesis", {
  model:  "fable",
  effort: "high",
  input:  { round1, dedupMap: round2 },
});

return stage3Input;   // feeds Stage 3 unchanged
```

Key orchestration properties (same guarantees as `/council` Round 1–3):
- Round 1 isolation is strict: no persona sees another's output during the sweep.
- Round 2 is dedup/rank, not re-hunting.
- Synthesis is a dedicated pass that reads all prior output with a merge
  responsibility explicit in its prompt — not the last persona to finish.

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
4. Every decomposed issue carries the correct state label (`ready-for-agent`, `blocked`, or `ready-for-human`).

**Completion criterion:** all four checks pass, or failing ones are fixed and re-verified before declaring done.

---

## Leverage-hunt catalog

See [`playbook.md`](./playbook.md) for what to look for under each leverage category — specific signals, patterns, and optional-input protocols.
