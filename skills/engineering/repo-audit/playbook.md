# Repo Audit — Playbook

Deep, on-demand reference for the `repo-audit` skill. Load this when you need
per-phase detail, the artifact policy, depth boosters, or the Phase 10
self-check protocol. The spine lives in `SKILL.md`.

---

## Phases

### Phase 0 — Setup & context ingestion

**Skill:** `project-claude-config`

Detect and, if needed, scaffold the project's Claude/agent config
(`.claude/`, `CLAUDE.md` / `AGENTS.md`, hooks). Map the repo layout (backend,
frontend, shared libs, infra, tests, CI/CD, docs, ADRs).

**Ground-truth summary — synthesize vs. grill.** Before asking the user
anything, check whether the repo carries strong, current ground-truth docs:
a `CLAUDE.md` / `AGENTS.md` covering project goals and constraints, a domain
glossary or `CONTEXT.md`, and ADRs that are not obviously stale. If those docs
exist and are internally consistent, *synthesize* the ground-truth summary
directly from them — faster and at least as accurate as grilling. Reserve
grilling (project goals, constraints, non-goals, risk tolerance, target
environments and users) for repos that lack those docs, or where the docs
appear stale or contradictory. When staleness or contradiction surfaces later
in the audit, feed it back as a docs-reconciliation finding (see depth-booster
4 and Phase 5); it need not block Phase 0 completion.

**Standing-automation inventory.** Enumerate every CI and scheduled workflow
in the repo (`.github/workflows/` or equivalent). Identify any standing audit
loops — scheduled jobs that already run staleness checks, architecture review,
agent-research scanning, or similar audit phases. For each planned audit phase
(1–9), decide:

- **Run** — no meaningful overlap; proceed in full.
- **Narrow** — a standing loop covers part of this phase; focus on what the
  loop misses (e.g. a per-PR architecture check won't catch cross-cutting
  seams).
- **Skip (covered by X)** — the standing loop covers this phase adequately;
  note which workflow and why.

Surface this per-phase decision table as part of the Phase 0 output, and let
it inform the depth question put to the user: existing coverage changes what a
full manual audit adds.

**Typical artifact:** An updated `CLAUDE.md` / `AGENTS.md` with project
overview, repo layout, and a "ground truth" system summary (main domains, key
user journeys, "do not break" areas), plus the standing-automation inventory
and per-phase run/narrow/skip table. This grounds all later phases in an
agreed-upon baseline.

**Feeds later phases:** Every subsequent phase reads the ground-truth summary
and the run/narrow/skip table to calibrate scope and risk tolerance.

---

### Phase 1 — Baseline scan & staleness audit

**Skill:** `staleness-audit`

Use `staleness-audit` to surface stale toolchain pins (runtime versions,
CI matrices, container tags). Layer on efficient code search to identify dead
code, unused modules, orphaned workflows, and outdated docs/ADRs. Quantify
codebase size and composition. Map the current test footprint (what types of
tests exist, where coverage is thin or absent). Flag GitHub issues and PRs
that are candidates for closure, merger, or rewrite.

**Typical artifact:** `docs/staleness-audit.md` — stale areas and recommended
deletions, "do not touch yet" areas with rationale, and a list of GitHub
issues/PRs scored for closure, rewrite, or reprioritization.

**Feeds later phases:** The deletion candidates feed Phase 2 (architecture);
the test-coverage map feeds Phase 3; the issues list feeds Phase 7.

---

### Phase 2 — Architecture & design review

**Skills:** `improve-codebase-architecture` · `software-design` · `ponytail-audit`

Run `improve-codebase-architecture` to identify deep vs shallow modules and
friction accumulation points. Apply `software-design` to evaluate
module/service boundaries, domain models, and design patterns. Overlay a
`ponytail-audit` lens: what can be deleted or radically simplified without
hurting users? Propose concrete deepening refactors with associated test
strategies; rate each suggestion (Strong / Worth exploring / Speculative).

**Typical artifact:** `docs/architecture-review.md` — before/after diagrams for
top changes, deep module analysis, strength-rated recommendations, and a
prioritized list of architecture improvements. Omit as a standalone doc only if
the repo is trivially small; fold findings into the master audit report with a
note.

**Feeds later phases:** The architecture findings shape what needs new tests
(Phase 3), what security boundaries matter (Phase 4), which PRDs are most
impactful (Phase 8), and how issues should be sliced (Phase 9).

---

### Phase 3 — Testing, quality & CI/CD

**Skill:** `tdd` principles

Define the critical behaviors that must be test-covered before major refactors
begin (`tdd`-style: tests lead the design). Audit the existing test strategy —
unit, integration, E2E, contract/snapshot — and identify flaky tests, brittle
patterns, and gaps. Review CI/CD: linting, type checks, test runs, security
scans, branch protections, and gating. Propose only incremental improvements
that do not destabilize existing pipelines.

**Typical artifact:** `docs/testing-strategy.md` — current vs target test
strategy, prioritized gaps, and a CI/CD improvements checklist with safety
rollout notes. Merge into the master audit report if the project is too trivial
to warrant a standalone doc.

**Feeds later phases:** The "must-cover before refactor" list constrains what
Phase 8 PRDs can propose as first steps.

---

### Phase 4 — Security & compliance

**Skill:** No dedicated repo skill — reason inline.

Apply a security-audit mindset directly: threat modeling (data flows, auth
boundaries), static code analysis patterns, dependency and secret handling,
workflow/CI security (token permissions, third-party actions). Group findings
by severity and ease of fix. Identify high-risk issues that must be addressed
before or alongside other work.

**Typical artifact:** A `docs/security-audit.md` only if there are material
security concerns or changes. If only trivial hygiene improvements surface,
summarize them in the master audit report with a "no dedicated artifact needed"
note. Never produce a standalone report just to have one.

**Feeds later phases:** High-severity findings block or reprioritize Phase 8
PRDs and become agent-ready issues in Phase 9.

---

### Phase 5 — Frontend, UX & docs

**Skills:** `frontend-design` · `doc-it`

Use `frontend-design` to assess visual design, hierarchy, layout, and
accessibility basics (contrast, semantics, keyboard use), plus implementation
patterns and code smell. Review UX flows end to end: onboarding, core tasks,
error handling, and empty states. Use `doc-it` to audit READMEs, architecture
docs, ADRs, API docs, onboarding guides, runbooks, and agent documentation.
Apply `doc-it`'s posture split: apply changes to reference docs; report ADR and
`CONTEXT.md` staleness without editing those files.

**Typical artifact:** `docs/frontend-review.md` for projects with meaningful UI;
fold into the master report for API-only or internal tooling. A doc update plan
(what to create, update, or delete). Skip `frontend-review.md` with a note for
repos with no UI surface.

**Feeds later phases:** Doc gaps inform Phase 8 (a "Docs & Agent Config" PRD
may be warranted); UX findings shape user stories in Phase 9.

---

### Phase 6 — Prior art & competitor analysis

**Skill:** `cba-searching`

Use `cba-searching` patterns to search GitHub and relevant ecosystems for
projects that already solve the same problem. Evaluate build-vs-buy-vs-
contribute. Identify any clearly overlapping approaches in the literature or
open-source landscape. Keep iterating until you either find strong overlap or
can articulate a clear argument for the project's unique or defensible scope.

**Typical artifact:** `docs/prior-art-and-competition.md` — overlaps, gaps,
unique value, pointers to relevant repos, and build/buy/contribute
recommendations. Fold into the master report if the repo is clearly internal
tooling with no novel aspects; note the rationale.

**Feeds later phases:** Prior-art findings sharpen Phase 8 PRD scoping (avoids
reinventing solved problems) and may prompt Phase 7 issue closures.

---

### Phase 7 — Backlog integration & triage

**Skills:** `triage` · repo label vocabulary

Ingest all open GitHub issues, PRs, and discussions. Cluster by theme
(architecture, bugs, UX/frontend, infra/CI, docs, experiments). Rewrite
unclear or noisy issues with clear problem statements, goals, and acceptance
criteria. Close or merge duplicates, stale requests, and out-of-scope items.

The following three steps are required, in order, before Phase 7 is considered
complete:

**1. Dedup first.** Every new finding from earlier phases (1–6) is
cross-checked against all open issues. Where there is meaningful overlap, fold
the finding into the existing issue (add context, update the description, link
the audit source) rather than creating a parallel entry. A new issue is only
warranted when no existing issue covers the same root cause or scope.

**2. One unified backlog.** New findings and existing issues are not two lists
— they are one. After dedup, order all surviving issues (pre-existing and
net-new) into a single priority sequence based on risk, impact, dependencies,
and the emerging roadmap from earlier phases. There is no "audit findings"
section sitting beside the regular backlog; everything lives in one ordered
set.

**3. Epic folding.** Group related issues — whether pre-existing or new — into
shared epics. Use existing epics where they fit; create new ones where a
coherent initiative spans multiple issues. Child issues are listed as
checklists in the epic body so the full initiative scope is visible in one
place.

**Typical artifact:** A unified, reprioritized backlog (closed/merged items,
rewritten and reprioritized issues, epics with child checklists) plus
`docs/backlog-notes.md` documenting triage rationale, priority semantics, and
the dedup log.

**Feeds later phases:** The unified backlog is the direct input for Phase 8
(which initiatives are PRD-worthy?) and Phase 9 (issue decomposition and
full-backlog triage).

---

### Phase 8 — Synthesis into PRDs & epics

**Skill:** `to-prd`

Aggregate key findings from all previous phases. Group work into named
initiatives (e.g., "Security Hardening", "Architecture Deepening",
"Test & CI Improvements", "UX Flow X", "Docs & Agent Config"). Use `to-prd`
to generate a PRD/epic for each initiative: clear problem, context, constraints,
measurable success criteria, dependencies, risks, and sequencing guidance that
keeps the app stable. Optionally produce a roadmap ordering the epics onto
milestones.

**Typical artifact:** PRDs as Markdown files in `docs/prd/` (or equivalent) and
an optional roadmap document ordered by initiative priority. Omit a roadmap if
there are fewer than three initiatives with meaningful sequencing constraints.

**Feeds later phases:** PRDs are the direct input to Phase 9 decomposition.

---

### Phase 9 — Decomposition & full-backlog triage

**Skills:** `to-issues` · `software-design` · `triage`

Use `to-issues` to decompose each PRD into vertical slices with explicit
dependency chains. Apply `software-design` where useful for internal design
sketches of complex tasks, edge-case coverage, and failure-mode analysis.
For each new issue, produce an agent-ready brief: user story or task
description, links to relevant files/docs/PRDs, constraints (security,
performance, UX, "do not break X"), and HITL tasks (explicit step-by-step
instructions or questions for humans).

**Triage over the full combined set.** Once new issues are decomposed and
merged into the unified backlog from Phase 7, run the `triage` skill's state
machine over every workable issue — new and pre-existing alike. Every workable
issue gets exactly one state label and the comment that label requires:

- `ready-for-agent` — a strong agent brief (context, acceptance criteria,
  constraints, HITL tasks). Maximize this category.
- `blocked` — a named, linked blocker and a concrete unblock path. No issue
  may sit in `blocked` without both.
- `ready-for-human` — agent-led instructions or explicit questions for the
  human owner.

**Close-candidates surfaced.** Where audit findings reveal that an existing
issue describes work that is already done, flag it explicitly. Propose closure
with a one-line rationale; close on confirmation.

**Typical artifact:** The final unified issue set — all issues triaged to a
state label with the required brief or comment, epics updated, close-candidates
flagged. Optionally, agent brief and HITL checklist templates for future use.

**Feeds Phase 10:** The final full issue set (new + existing, fully triaged) is
the input to the self-check.

---

### Phase 10 — Multi-role self-check & safety rails

**Skill:** Owned by this skill (no delegation).

Re-review all artifacts through five distinct internal roles:

- **Architect** — are module boundaries and design choices internally
  consistent? Do the PRDs respect the architecture findings?
- **Tester** — is every significant behavior or change covered by a test plan
  or a Phase 3 gap entry?
- **Security engineer** — do any proposed changes introduce new attack surface
  or bypass controls identified in Phase 4?
- **Product manager** — are all issues scoped to a clear user or business
  outcome? Are priorities defensible?
- **Lazy senior dev (Ponytail)** — is there anything in the backlog we should
  simply not build? Any PRD that could be replaced by deleting code?

Cross-check for contradictions and inconsistencies across reports, PRDs, and
issues. Flag unsafe changes (security, data loss, reliability risks). Surface
gaps between docs and code. Re-run targeted phases when contradictions are
found or major blind spots are detected.

**Completion gate (explicit pass/fail).** The five-role review above is
necessary but not sufficient. The self-check FAILS — and phases must be
revisited — if any of the following are true:

- Any new issue was filed without being integrated into the unified backlog
  (i.e. dedup, epic folding, and ordering were not applied).
- Any workable issue lacks a state label, or lacks the required brief or
  comment for that label.
- Any issue carrying `blocked` lacks a named, linked blocker and an unblock
  path.

The self-check passes only when every item in the unified backlog satisfies
these conditions.

**Typical artifact:** `docs/audit-summary.md` — main findings and decisions,
top initiatives with rationale, how the backlog and roadmap were derived, and
a "known unknowns" list of areas of uncertainty with suggested follow-up
explorations.

---

## Depth boosters

These cross-cut multiple phases. Apply them wherever they add signal.

### 1. Red team / abuse-case pass

Design abuse cases and failure modes (privilege escalation, data exfiltration,
feature-flag misuse, etc.) and map them to code paths, tests, and CI checks.
Emit issues where coverage is absent. Best run during or after Phase 4.

### 2. Data-flow & dependency analysis

Produce diagrams showing how data and control flow across services, queues, and
external APIs. Use the results to spot tight coupling, god modules/services, and
hidden dependencies. Best run alongside Phase 2.

### 3. Performance & scalability sensibility checks

Identify obvious hot paths, N+1s, heavy queries, and scaling risks from
architecture and code patterns. Suggest high-level remediation and flag where
more measurement is warranted before optimization. Best run after Phase 2.

### 4. Documentation vs reality reconciliation

Explicitly mark where docs and ADRs disagree with code, tests, or actual
behavior. Decide whether to update docs, realign code, or both. This is
`doc-it`'s report-only posture applied aggressively — surface every mismatch.
Best run during Phase 5.

### 5. Post-fix mini-audit loop

Recommend re-running a targeted mini-audit on high-risk areas after key fixes
land. This confirms findings are resolved and guards against regression. Best
described in Phase 10 as a follow-up recommendation, not a Phase 10 action
(the fixes haven't happened yet at audit time).

---

## Artifact policy

**Evidence-driven, not process-driven.** The suggested core artifact set below
is a default, not a checklist to complete mechanically.

Use judgment: if a domain surfaces no meaningful findings, risks, or decisions,
either omit the standalone artifact or merge it into the master audit report.
Any omitted, merged, or downgraded artifact requires a one-line rationale.
**Prefer one strong synthesis over multiple thin artifacts.**

### Suggested core artifact set

| Artifact | Default stance |
|----------|---------------|
| Master audit report | Always suggested — the central synthesis. |
| Architecture review | Strongly suggested for non-trivial repos. |
| Testing & CI/CD review | Suggested unless the project is trivially simple. |
| Security notes or report | Suggested; dedicated artifact only if there are material concerns. |
| UX/frontend review | Suggested for projects with meaningful UI. |
| Docs & meta review | Suggested where docs, ADRs, or agent config exist or clearly should. |
| Backlog triage output | Strongly suggested — a core goal of the audit. |
| Prior-art / competitor notes | Suggested when the project overlaps with existing tools or approaches. |
| PRDs and epics | Suggested when audit identifies substantive follow-on work. |
| Decomposed agent-ready issues | Suggested where PRDs exist and work is realistically delegable. |
