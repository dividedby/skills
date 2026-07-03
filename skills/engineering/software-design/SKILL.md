---
name: software-design
disable-model-invocation: true
description: >
  Orchestrates a multi-module design session — prereq self-check, frontend
  routing stamp, issue clustering, module/seam design via codebase-design,
  TDD-ready issue rewrite, and batch tracker mutation — for a PRD + published
  backlog that spans two or more modules. Use when module and seam choices are
  still implicit after /to-issues has run.
---

# Software Design

This skill turns a PRD and a published backlog into a clear design: named
modules, located seams, an explicit testing strategy, and TDD-ready issue
bodies that `/tdd` or `/implement` can carry one behavior at a time.

It is an **orchestration wrapper**: the deep-module/seam vocabulary and
testability doctrine live in `/codebase-design`; the ubiquitous-language
grounding lives in `/domain-modeling`. This skill calls both and contributes
the glue they lack — the prereq gate, the frontend routing stamp, the
confirmation loop, and the batch tracker mutation.

Backend services and code with real I/O boundaries are the sharpest use
case. UI component trees route to `/frontend-design` — this skill stamps the
routing block and hands off; it does not design components.

---

## When to Run

Run after:

- A PRD or epic exists (in conversation, in a file, or as a parent issue).
- `/to-issues` has published a backlog of issues for that epic.
- `CONTEXT.md` exists with the domain vocabulary the issues will use.

It is at its sharpest when the backlog plausibly spans **two or more
modules** and module/seam choices are still implicit. If those conditions
aren't met, apply the early-exit rule below or suggest the user run the
missing prerequisite skill.

---

## When to Skip

The skill exits early if any of these is true:

- The change is a single-module tweak, a copy edit, a one-line bugfix, or
  any work that fits inside one existing module without crossing a seam.
- The backlog has ≤2 issues and they touch the same domain concept.
- The work is exploratory or throwaway and the boundaries are intentionally
  disposable.

Early-exit behavior has two paths:

- **Backend single-module** — post `design-skipped: single-module change`
  on each affected issue and tell the user to run `/tdd` or `/implement`
  directly.
- **UI-only** — post `routed-to: /frontend-design` on each affected
  issue and tell the user to run `/frontend-design` next, then `/tdd` or
  `/implement`.

Even on early-exit, the stamping pass (step 2) still runs for every
frontend-flavored issue.

---

## Self-Check on Invocation

Before doing anything else, verify the prerequisites:

1. **PRD or epic context** — is there a PRD file, a parent issue, or a
   conversation context that names the feature? If not, stop and tell the
   user to establish the PRD first (e.g. via `/to-prd`).
2. **`CONTEXT.md` exists** — if absent, stop and tell the user to run
   `/grill-with-docs` first to establish domain vocabulary.
3. **Issues to design against** — fetch open issues for the epic via the
   tracker (per `docs/agents/issue-tracker.md`). If none, stop and tell the
   user to run `/to-issues` first.
4. **Likely multi-module** — read the issue set. If it plausibly spans 2+
   modules, proceed. Otherwise apply the early-exit rule above.

---

## Workflow

### 1. Gather context

Read, in order:

- `CONTEXT.md` for the domain vocabulary used in the issues
- `docs/adr/` for prior architecture decisions in the affected area
- The PRD (issue body, file, or conversation context)
- All open issues in the epic, with comments and labels

Do not begin design until you have read the glossary. Use its terms for
every module name, interface, and rewritten issue.

**Challenge inherited choices.** CONTEXT.md, ADRs, and the current stack
often predate this skill. If a prior decision is a poor fit for the
backlog — wrong persistence model, wrong sync/async boundary, a stack
that fights the seams you're about to draw — name the mismatch explicitly.
Surface one proposal with the tradeoff in plain terms; let the user accept
(and defer the revision to `/grill-with-docs` for an ADR) or override.
Do not silently inherit a bad fit just because it's already written down.

### 2. Stamp frontend-flavored issues with the routing block

Before any module/seam work, scan every open issue. An issue is
**frontend-flavored** when two of these three signals are true:

1. **Output surface is visible** — a page, screen, component, modal, form,
   chart, theme, or layout. Keyword smell: *renders, displays, shows, page,
   screen, component, modal, form, button, layout, theme, responsive*.
2. **Module responsibility is presentational** — the cluster lands in a
   module whose one reason to change is presentation. A pure data module
   with a downstream UI consumer does not count.
3. **Acceptance criteria mention visual or interaction behavior** — color,
   spacing, focus state, hover, animation, accessibility, responsive
   breakpoints.

For each frontend-flavored issue, stamp a `**Frontend design**` routing
block into the body — even if the backlog is small enough that the rest of
the skill will early-exit. Uniformity beats optimisation.

The block carries: Stack (from the project's package manifest), Intent
(paraphrase of the Behavior line), Aesthetic direction (path to
`docs/design/direction.md`), Token authority (path read from that file),
and Review (required only when AC explicitly mention a11y / contrast /
design audit). Full field spec lives in
`skills/engineering/frontend-design/direction-doc-format.md`.

Write field values mechanically from the project's manifest and direction
doc. Do not ask the user about typography, color, or motion. Backend-only
issues get no stamp.

### 3. Cluster issues by domain concept

Group issues by the concept they touch. A cluster is a coherent set of
responsibilities that changes for the same reasons. Label each cluster with
a domain noun from `CONTEXT.md`.

One signal for the cuts: which issues cross a communication boundary
(sync/async, external system)? That's a seam, not a module cut — it tells
you where an adapter goes.

### 4. Invoke `/codebase-design` for module/seam vocabulary and design

Invoke `/codebase-design` to apply the deep-module/seam framework to the
clustered issue set. The module/seam vocabulary, the deletion test, the
decomposition heuristics, the adapter strategy, and the testability
principles all live there — not here.

For each module, surface:

- **Name** — from domain vocabulary
- **Responsibility** — one reason to change
- **Interface** — commands, queries, events (not implementation)
- **Invariants** — rules this module owns
- **Depends on** — other modules or seams
- **Must not depend on** — e.g., transport layer, persistence

### 5. Invoke `/domain-modeling` for ubiquitous-language grounding

Hand `/domain-modeling`:

- The candidate module names from step 4
- All interface operation names and event names the design session surfaced
- The current `CONTEXT.md` glossary as reference

Expect back:

- Confirmation or correction of each term against the project's ubiquitous
  language (e.g. "OrderPlaced not OrderCreated — see CONTEXT.md §Events")
- A flagged list of any surfaced terms not yet in `CONTEXT.md`, each
  needing `/grill-with-docs` extraction before or after this session

Incorporate the canonical terms before presenting the module map to the
user. Any flagged new terms are surfaced in step 7.

### 6. Confirm with user

Render the module map — using only the canonical terms confirmed in step 5
— as a short summary. Ask:

- Does the responsibility split feel right?
- Are there missing modules or collapsed responsibilities?
- Do the seam locations match where change is expected?

Iterate. Do not proceed to step 7 without approval.

### 7. Surface durable items for extraction

As the design session surfaces new domain terms or hard trade-offs, **do
not write them yourself**. Surface them and defer to the responsible skill:

- A new domain term → "this term isn't in `CONTEXT.md`. Capture it via
  `/grill-with-docs` discipline now, or defer?"
- A hard-to-reverse trade-off with real alternatives → "this looks
  ADR-worthy. Write an ADR via `/grill-with-docs` now, or defer?"

`CONTEXT.md` and `docs/adr/` are owned by `/grill-with-docs`.

### 8. Invoke `/council` for adversarial design review (advisory)

Hand `/council` the confirmed module map from step 6 and the strongest open
objections surfaced so far — hard-to-reverse seam decisions, unresolved
trade-offs, or any conclusion the team has already convinced itself of. These
emerge naturally across steps 3–7 as clusters are cut, modules named, and
durable items flagged.

`/council` returns its standard four-block output (Synthesis, Rationale,
Panel Dissent, Confidence). Append the Panel Dissent block — and any
synthesis point that names a risk the design session did not surface — as an
advisory "panel dissent" section. Present it to the user alongside the
confirmed design. Ask whether to proceed to step 9 or revisit any module
decisions. The user ratifies; this skill does not.

**Advisory only.** The council output never gates issue carving. It is
additional evidence, not a veto.

**Graceful degradation.** If the Workflow tool is unavailable, `/council` is
explicitly skipped, or the invocation fails for any reason, note the skip in
the conversation and proceed directly to step 9. This sub-step is an
advisory enrichment, not a structural requirement.

### 9. Rewrite issue bodies into the TDD-ready format

For each issue, rewrite the body. Each rewritten issue is one observable
behavior. Required fields, in order: **Module** (canonical name from step
5), **Behavior** (actor / behavior / value), **Acceptance criteria**
(Given/When/Then, independently verifiable), **Frontend design** (stamped
in step 2; omit for backend-only issues), **TDD notes** (entry point by
name not path, test-first target, edge cases, fake strategy, must-NOT-test
list).

Name behaviours, interfaces, and types — not file paths or line numbers.
State *what* the system should do in observable Given/When/Then form, not
*how* to wire it.

Split any issue that mixes modules. After splitting and rewriting, order
the full set: **tracer bullet first** (the issue that proves the path works
end-to-end), then core behavior, then edge cases, then integration.

### 10. Propose all mutations as a single batch

Before writing anything to the tracker or to disk, render the full set of
changes in conversation:

- All rewritten issue bodies
- The Design Plan content for `docs/design/<feature>.md`

The Design Plan records modules, seams, testing strategy, invariants, and a
one-line issue index linking to each rewritten issue. It does not duplicate
issue bodies — the issue tracker is authoritative for those.

The Design Plan file (`docs/design/<feature>.md`) contains, in order:
title, status/date/epic header; **Context** (one paragraph, domain
vocabulary only); **Domain Vocabulary Used** (terms from CONTEXT.md this
plan relies on); **Module Map** (module → responsibility → interface
operations → seams); **Seams** (what crosses each boundary, adapter in
tests vs prod); **Invariants and Contracts** (rules that must hold
regardless of implementation); **Testing Strategy** (module → test entry
point → test level → fake strategy); **Issue Index** (issue → module →
one-line description); **Open Questions** (unresolved before or during
implementation).

Wait for explicit approval. Apply inline edits the user requests. Then
write everything in one pass via the tracker (`gh issue edit`) and the
filesystem.

The skill never mutates external state without one batch approval.

---

## Stale Design Plans

The Design Plan is short-lived implementation scaffolding. When the user
notices drift from reality, they handle it inline: add a callout at the
affected section, then extract any durable lesson via `/grill-with-docs`.

After the last issue ships, mark the Design Plan `status: shipped`.

---

## Checklist Per Design Session

```
[ ] Self-check passed (PRD, CONTEXT.md, issues, multi-module signal)
[ ] Domain vocabulary read from CONTEXT.md before naming anything
[ ] Frontend-flavored issues stamped (step 2) regardless of backlog size
[ ] /codebase-design invoked for module/seam framework (step 4)
[ ] /domain-modeling invoked before user confirmation; canonical terms incorporated (step 5)
[ ] Each module has exactly one reason to change
[ ] No issue mixes responsibilities from two modules
[ ] Issues ordered: tracer bullet → core behavior → edge cases → integration
[ ] New terms or trade-offs surfaced for /grill-with-docs extraction
[ ] /council invoked on confirmed design; Panel Dissent block appended and reviewed (or skip noted)
[ ] Full batch of rewrites previewed and approved before writing
[ ] Design Plan written and linked from affected issues
```
