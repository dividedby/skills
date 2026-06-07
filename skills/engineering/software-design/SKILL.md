---
name: software-design
description: >
  Designs modules, seams, and a testing strategy for a multi-issue backlog
  after a PRD exists and /to-issues has published issues, and before /tdd
  begins implementation. Use when the backlog plausibly spans two or more
  modules and module/seam choices are still implicit.
---

# Software Design

This skill turns a PRD and a published backlog into a clear design: named
modules, located seams, an explicit testing strategy, and TDD-ready issue
bodies that `/tdd` can implement one behavior at a time.

This skill thinks in **modules, seams, and adapters**. It is sharpest for
backend services and code with real I/O boundaries. Small CLIs and pure
data pipelines usually hit the early-exit instead. UI component trees
route to `/frontend-design` — this skill stamps the routing block onto
frontend-flavored issues and hands off; it does not design components.

See [modules-and-seams.md](modules-and-seams.md) for module and seam
vocabulary, [testability.md](testability.md) for designing interfaces tests
love, [issue-shape.md](issue-shape.md) for the TDD-ready issue body format,
and [design-plan-format.md](design-plan-format.md) for the Design Plan
template.

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

Even on early-exit, the stamping pass below still runs for every
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

This skill is its own gatekeeper.

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
backlog you're about to design against — wrong persistence model, wrong
sync/async boundary, a stack that fights the seams you're about to draw,
a library choice that's since been superseded — name the mismatch
explicitly. Surface one proposal with the tradeoff in plain terms; let
the user accept (and defer the revision to `/grill-with-docs` for an
ADR) or override. Do not silently inherit a bad fit just because it's
already written down.

### 2. Stamp frontend-flavored issues with the routing block

Before any module/seam work, scan every open issue against the
two-of-three frontend detection rule in
[issue-shape.md](issue-shape.md). For each frontend-flavored issue,
stamp the `**Frontend design**` routing block into the body — even if
the backlog is small enough that the rest of the skill will early-exit,
and even if only one issue qualifies. Uniformity beats optimisation.

Write the field values mechanically per the **Stamping Rule** in
[issue-shape.md](issue-shape.md) — including the conditional `Review`
field, added only when the issue's acceptance criteria call for an
accessibility, contrast, or design audit. Do not interpret the pointers.
Do not open `docs/design/direction.md`. Do not ask the user about
typography, color, or motion — those belong to `/frontend-design`.

Backend-only issues get no stamp; the block is omitted entirely.

### 3. Cluster issues by domain concept

Group issues by the concept they touch. A cluster is a coherent set of
responsibilities that changes for the same reasons. Apply the
**Decomposition Heuristics** in [modules-and-seams.md](modules-and-seams.md)
to find the cuts.

One signal those heuristics don't name: which issues cross a communication
boundary (sync/async, external system)? That's a seam, not a module cut —
it tells you where an adapter goes.

Label each cluster with a domain noun from `CONTEXT.md`.

### 4. Propose modules and seams

For each cluster, propose one or more modules. A module is anything with an
interface and an implementation. A seam is where that interface lives.

Apply the deletion test from [modules-and-seams.md](modules-and-seams.md):
if you deleted this module, would complexity vanish or reappear elsewhere?
Reappearance means the module earns its keep.

For each module, capture:

- **Name** — from domain vocabulary
- **Responsibility** — one reason to change
- **Interface** — commands, queries, events (not implementation)
- **Invariants** — rules this module owns
- **Depends on** — other modules or seams it may call
- **Must not depend on** — e.g., transport layer, persistence

### 5. Confirm with user

Render the module map as a short summary (not a wall of text). Ask:

- Does the responsibility split feel right?
- Are there missing modules or collapsed responsibilities?
- Do the seam locations match where change is expected?

Iterate. Do not proceed to step 6 without approval.

### 6. Define the testing strategy

For each module, decide:

- The test entry point (public interface, not internals)
- Which layer owns unit-level tests vs integration-level tests
- Which seams need a fake/stub adapter vs a real one

Use [testability.md](testability.md) to shape interfaces for test clarity.
Use [modules-and-seams.md](modules-and-seams.md) to decide where fakes go.

### 7. Surface durable items for extraction

As the design session surfaces new domain terms or hard trade-offs, **do
not write them yourself**. Surface them and defer to the responsible skill:

- A new domain term → "this term isn't in `CONTEXT.md`. Capture it via
  `/grill-with-docs` discipline now, or defer?"
- A hard-to-reverse trade-off with real alternatives → "this looks
  ADR-worthy. Write an ADR via `/grill-with-docs` now, or defer?"

`CONTEXT.md` and `docs/adr/` are owned by `/grill-with-docs`. This skill
points at them; it does not extend them.

### 8. Rewrite issue bodies into the TDD-ready format

For each issue, rewrite the body using the format in
[issue-shape.md](issue-shape.md):

- Module assignment
- Behavior statement (user-story shape)
- Acceptance criteria (Given/When/Then)
- TDD notes — entry point, test-first behavior, edge cases, fake strategy, must-not-test

Split any issue that mixes modules. Each rewritten issue is one observable
behavior. After splitting and rewriting, order the full set per the
tracer-bullet rule in [issue-shape.md](issue-shape.md): tracer bullet first,
then core behavior, then edge cases, then integration.

### 9. Propose all mutations as a single batch

Before writing anything to the tracker or to disk, render the full set of
changes in conversation:

- All rewritten issue bodies
- The Design Plan content for `docs/design/<feature>.md`

Wait for explicit approval. Apply inline edits the user requests. Then
write everything in one pass via the tracker (`gh issue edit`) and the
filesystem.

The skill never mutates external state without one batch approval.

### 10. Write the Design Plan

Create `docs/design/<feature-name>.md` using
[design-plan-format.md](design-plan-format.md). The plan records modules,
seams, testing strategy, invariants, and a one-line **issue index**
linking to each rewritten issue. It does not duplicate issue bodies — the
issue tracker is authoritative for those.

---

## Stale Design Plans

The Design Plan is short-lived implementation scaffolding. It will drift
from reality as `/tdd` reveals corrections — a misplaced seam, an absorbed
responsibility, a broken invariant.

When the user notices drift, they handle it inline:

- Add a callout at the affected section of the Design Plan.
- Extract any durable lesson via `/grill-with-docs` to `CONTEXT.md` or
  `docs/adr/`.

Example inline callout, added directly under the affected section heading:

```markdown
## Seams

> **Stale:** `PaymentGateway` was split into `PaymentAuthorizer` and
> `PaymentCapture` during implementation — the two-phase auth flow forced
> the split. See #47 and ADR-0009.
```

No frontmatter status flag for stale. No formal re-run. If the drift is
large enough that the plan is unrecoverable, the user can re-invoke
`/software-design` on the remaining issues — but that is the user's call,
not the skill's prescription.

After the last issue ships, mark the Design Plan `status: shipped`. Future
agents read `CONTEXT.md` and ADRs first; the Design Plan stays in
`docs/design/` for historical context only.

---

## Checklist Per Design Session

```
[ ] Self-check passed (PRD, CONTEXT.md, issues, multi-module signal)
[ ] Domain vocabulary read from CONTEXT.md before naming anything
[ ] Each module has exactly one reason to change
[ ] Each seam is named in domain language with a recorded adapter strategy
[ ] No issue mixes responsibilities from two modules
[ ] Issues ordered within the epic: tracer bullet → core behavior → edge cases → integration
[ ] Testing entry points are public interfaces, not internals
[ ] New terms or trade-offs surfaced for /grill-with-docs extraction
[ ] Full batch of rewrites previewed and approved before writing
[ ] Design Plan written and linked from affected issues
```

---

## Anti-Patterns

**Do not design by layer** (controller, service, repository). Layers are
implementation structure, not design boundaries. Design by behavior and
domain concept.

**Do not add modules speculatively.** Only propose a module if at least
one current issue requires it. YAGNI applies to design too.

**Do not over-specify the interface.** The Design Plan records *what* the
interface looks like, not *how* it is implemented. No file paths, class
names, or library choices — those go stale.

**Do not write to `CONTEXT.md` or `docs/adr/` from this skill.** Surface
the need and defer. `/grill-with-docs` owns those files.

**Do not mutate the tracker or disk per-issue.** One batch preview, one
approval, one pass.

**Do not design components, pages, or visual systems in this skill.**
Frontend-flavored issues get the `**Frontend design**` routing block
stamped onto their bodies and route to `/frontend-design`. This skill
never speaks of directions, tokens, typography, color, or motion —
those belong to `/frontend-design`.
