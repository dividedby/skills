---
name: software-design
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
bodies that `/tdd` can implement one behavior at a time.

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
  on each affected issue and tell the user to run `/tdd` directly.
- **UI-only** — post `routed-to: /frontend-design` on each affected
  issue and tell the user to run `/frontend-design` next, then `/tdd`.

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

For each frontend-flavored issue, stamp the `**Frontend design**` routing
block into the body — even if the backlog is small enough that the rest of
the skill will early-exit. Uniformity beats optimisation.

The **Frontend design** block fields:

```
**Frontend design** (invoke `/frontend-design` before `/tdd`):
- Stack: <read from the project's package manifest / framework config>
- Intent: <paraphrase the Behavior: line>
- Aesthetic direction: see docs/design/direction.md
- Token authority: <path from docs/design/direction.md, or "recorded in docs/design/direction.md">
- Review: required           ← only when AC explicitly mention a11y / contrast / design audit
```

Write the field values mechanically. Do not open `docs/design/direction.md`.
Do not ask the user about typography, color, or motion. Backend-only issues
get no stamp.

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

### 5. Confirm with user

Render the module map as a short summary. Ask:

- Does the responsibility split feel right?
- Are there missing modules or collapsed responsibilities?
- Do the seam locations match where change is expected?

Iterate. Do not proceed to step 6 without approval.

### 6. Invoke `/domain-modeling` for ubiquitous-language grounding

Invoke `/domain-modeling` to ground every module name, interface operation,
and event name in the project's ubiquitous language. Any term the design
session surfaced that isn't yet in `CONTEXT.md` gets flagged here for
`/grill-with-docs` extraction.

### 7. Surface durable items for extraction

As the design session surfaces new domain terms or hard trade-offs, **do
not write them yourself**. Surface them and defer to the responsible skill:

- A new domain term → "this term isn't in `CONTEXT.md`. Capture it via
  `/grill-with-docs` discipline now, or defer?"
- A hard-to-reverse trade-off with real alternatives → "this looks
  ADR-worthy. Write an ADR via `/grill-with-docs` now, or defer?"

`CONTEXT.md` and `docs/adr/` are owned by `/grill-with-docs`.

### 8. Rewrite issue bodies into the TDD-ready format

For each issue, rewrite the body. Each rewritten issue is one observable
behavior, in this shape:

```
**Module**: <module name>

**Behavior**: As a <actor>, I can <behavior> so that <value>.

**Acceptance criteria**:
- Given <precondition>, when <action>, then <observable outcome>
- ...

**Frontend design** (invoke `/frontend-design` before `/tdd`):
- ...                ← frontend-flavored issues only; see step 2

**TDD notes**:
- Entry point: <public function / command / endpoint — name, not file path>
- Test first: <most critical behavior>
- Edge cases: <list>
- Fake strategy: <what to fake, at which seam>
- Must NOT test: <internal details to avoid coupling>
```

Name behaviours, interfaces, and types — not file paths or line numbers.
State *what* the system should do in observable Given/When/Then form, not
*how* to wire it. Make acceptance criteria independently verifiable.

Split any issue that mixes modules. After splitting and rewriting, order
the full set: **tracer bullet first** (the issue that proves the path works
end-to-end), then core behavior, then edge cases, then integration.

### 9. Propose all mutations as a single batch

Before writing anything to the tracker or to disk, render the full set of
changes in conversation:

- All rewritten issue bodies
- The Design Plan content for `docs/design/<feature>.md`

The Design Plan records modules, seams, testing strategy, invariants, and a
one-line issue index linking to each rewritten issue. It does not duplicate
issue bodies — the issue tracker is authoritative for those.

Design Plan template:

```markdown
# Design Plan: <Feature Name>

> Status: approved | shipped
> Created: YYYY-MM-DD
> Epic: <PRD link or parent issue>

## Context
<One paragraph: problem, audience, why now. Domain vocabulary only.>

## Domain Vocabulary Used
<Terms from CONTEXT.md this plan relies on.>

## Module Map
| Module | Responsibility | Interface (operations) | Seams |

## Seams
| Seam | What crosses it | Adapter in tests | Adapter in prod |

## Invariants and Contracts
<Rules that must hold regardless of implementation.>

## Testing Strategy
| Module | Test entry point | Test level | Fake strategy |

## Issue Index
| Issue | Module | One-line description |

## Open Questions
<Questions needing resolution before or during implementation.>
```

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
[ ] /domain-modeling invoked for ubiquitous-language grounding (step 6)
[ ] Each module has exactly one reason to change
[ ] No issue mixes responsibilities from two modules
[ ] Issues ordered: tracer bullet → core behavior → edge cases → integration
[ ] New terms or trade-offs surfaced for /grill-with-docs extraction
[ ] Full batch of rewrites previewed and approved before writing
[ ] Design Plan written and linked from affected issues
```
