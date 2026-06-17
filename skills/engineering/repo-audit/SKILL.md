---
name: repo-audit
description: >
  Multi-phase orchestrator that audits an arbitrary software project end-to-end —
  code, tests, CI/CD, security, docs, GitHub issues — and converts findings into
  prioritized PRDs and agent-ready issues while never breaking the working app.
  Delegates every domain to the appropriate sub-skill; owns only sequencing and
  synthesis. Use when asked to "audit this repo", "do a deep repo audit",
  "audit and plan", "turn this repo into a backlog", "comprehensive code review",
  or "full project health check".
---

# Repo Audit

A **runbook of runbooks**. This skill sequences existing skills across a target
repo's full surface and synthesizes findings into a prioritized backlog and
agent-ready issues. It never re-implements logic that a sub-skill already owns.

## When to use

- You want a holistic view of a repo you've inherited or are starting serious
  work on.
- The backlog has drifted from the actual codebase and needs a ground-truth
  reset.
- You're planning a significant refactor or feature expansion and want to
  derisk it first.

## When not to use

- You need just one domain: reach for `staleness-audit`, `tdd`,
  `improve-codebase-architecture`, etc. directly.
- The project is too early-stage to audit (no code yet, prototype only).
- You only need a quick PR review or a single-file fix.

## Operating principles

- **Repo- and language-agnostic.** Assume nothing about structure, stack, or
  CI system until you read the repo.
- **Lazy-senior-dev energy.** Channel `ponytail-audit`: ruthless simplification
  and deletion over accretion. The best code is often the code you never write.
- **Architecture first.** Run `improve-codebase-architecture` early so later
  work lands on sane, testable boundaries.
- **Evidence-backed.** Every recommendation traces to code, tests, history, or
  search — not vibes. Honesty over comfort: call out tech debt and dead code
  candidly.
- **Keep the app working.** Bias toward safe, incremental changes and guardrails
  in CI. Strong test coverage over risky rewrites. Surface any conflict between
  an audit finding and repo-specific constraints explicitly; prefer preserving a
  working system.
- **Prefer one strong synthesis over many thin artifacts.** Skip or merge an
  artifact when there is no real signal, and note why.
- **Complement, don't duplicate, standing automation.** Phase 0 enumerates
  existing CI/scheduled audit loops; each phase is then scoped to what the
  standing automation misses, not run in full regardless.

## Prerequisites

This skill sequences other skills, several of which are **not in this repo** — they live in the maintainer's global environment (`~/.claude/skills/`). The canonical snapshot of what's expected to be present is [`docs/agents/installed-skills.md`](../../../docs/agents/installed-skills.md).

External (installed) skills used by the phases below:

| Skill | Phase(s) |
|-------|----------|
| `improve-codebase-architecture` | 2 |
| `ponytail` plugin (ponytail-audit lens) | 2 |
| `tdd` | 3 |
| `cba-searching` | 6 |
| `to-prd` | 8 |
| `to-issues` | 9 |

Skills used by the phases that **are** in this repo (no install needed): `project-claude-config` (Phase 0), `staleness-audit` (Phase 1), `software-design` (Phases 2, 9), `frontend-design` (Phase 5), `doc-it` (Phase 5), `triage` (Phases 7, 9).

If a phase's skill is absent from the running environment, surface it explicitly at the start of that phase and either skip the phase (with a recorded rationale) or apply the skill's documented reasoning inline — consistent with the Phase 0 narrow/skip protocol.

## Phase table

| # | Phase | Primary skill(s) |
|---|-------|-----------------|
| 0 | Setup & context ingestion | `project-claude-config` |
| 1 | Baseline scan & staleness | `staleness-audit` |
| 2 | Architecture & design review | `improve-codebase-architecture` · `software-design` · `ponytail-audit` |
| 3 | Testing, quality & CI/CD | `tdd` principles |
| 4 | Security & compliance | inline reasoning (no dedicated skill — see playbook) |
| 5 | Frontend, UX & docs | `frontend-design` · `doc-it` |
| 6 | Prior art & competitors | `cba-searching` |
| 7 | Backlog integration & triage | `triage` · repo label vocabulary |
| 8 | Synthesis into PRDs & epics | `to-prd` |
| 9 | Decomposition & full-backlog triage | `to-issues` · `software-design` · `triage` |
| 10 | Multi-role self-check & safety rails | owned by this skill |

## Hard rules

- Delegate each phase to the named skill; never re-implement what that skill
  already documents.
- When a repo-specific constraint conflicts with a finding, surface the conflict
  explicitly and propose alternatives before acting.
- Prefer one strong synthesis artifact (master audit report) over many thin
  stand-alone docs. Skip or merge domain artifacts that show no material signal,
  and record a one-line rationale for each omission.
- Phases 7–9 are NOT complete until new findings are integrated INTO the
  existing backlog as one reprioritized, fully-triaged whole. New issues must
  never be filed as a flat list alongside existing issues without dedup, epic
  folding, and state-label triage applied across the full combined set.

## Depth boosters and per-phase detail

See [`playbook.md`](./playbook.md) for the deep, on-demand reference: what each
phase inspects, its typical artifact, how it feeds later phases, the five depth
boosters, the full artifact policy, and the Phase 10 multi-role self-check
protocol.
