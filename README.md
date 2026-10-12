# Skills

My personal Claude Code skills.

## Install

```bash
pnpm dlx skills@latest add dividedby/skills
```

Pick the skills you want when prompted. Re-run to update.

## Skills

### Engineering

- **[autonomous-loop](./skills/engineering/autonomous-loop/SKILL.md)** — Take a briefed backlog to a safely-running unattended (AFK) agent loop: runtime selection, stop condition, per-iteration feedback gates, HITL→AFK graduation-by-guardrail with a cap, and monitor/stop/resume. Methodology, not a runtime.
- **[council](./skills/engineering/council/SKILL.md)** — Convene a blind, diverse multi-persona panel (Falsifier, Minimalist, Pragmatist + conditional seats) that returns a synthesized second opinion plus the dissent the chair did not adopt; drives the built-in Workflow tool across three rounds.
- **[doc-it](./skills/engineering/doc-it/SKILL.md)** — Scan a repo and generate or patch its reference documentation (README, API docs, onboarding guide, CHANGELOG) from source, applying changes directly; audits ADRs and CONTEXT.md for staleness but reports findings only.
- **[flow-pr](./skills/engineering/flow-pr/SKILL.md)** — End-to-end flow-aware PR helper: reads the repo's default branch as the integration target, cuts a feature branch, commits → pushes → opens PR against the default branch, reviews and fixes the diff (via `/code-review`), gates on CI green, then merges. Promotion (default→main) is always-confirmed and only applies when the default branch is not main.
- **[frontend-design](./skills/engineering/frontend-design/SKILL.md)** — Design, refine, and audit production-grade frontend interfaces across React, Next.js, Tailwind, and vanilla HTML/CSS/JS that avoid generic AI aesthetics.
- **[repo-audit](./skills/engineering/repo-audit/SKILL.md)** — User-invoked audit that hunts high-leverage improvements in a repo (delete/lean, performance, architectural deepening, missing features) and produces a small set of epics with an ordered roadmap — reconciled against the existing backlog, not filed beside it.
- **[software-design](./skills/engineering/software-design/SKILL.md)** — Turns a PRD and published backlog into named modules, located seams, and a testing strategy that makes issues TDD-ready.
- **[staleness-audit](./skills/engineering/staleness-audit/SKILL.md)** — Audit a repo's pinned toolchain versions (Node, Python, Go, container and CI matrices) for staleness and emit a ranked report — safe in-major bumps auto-applied behind a verify gate, cross-major / EOL jumps stay recommendations; the complement to Dependabot's library bumps.
- **[write-well](./skills/engineering/write-well/SKILL.md)** — Draft and de-slop English prose to a defensible core and clean output; two entry points (draft, improve).

### Config

Setting up and auditing a project's Claude config — instruction files and the settings/hooks harness. See the [bucket README](./skills/config/README.md) for the internal seams.

- **[project-claude-config](./skills/config/project-claude-config/SKILL.md)** — One state-routed pass over a project's Claude config: scaffold what's missing and critique what's present across both the harness (`.claude/settings.json`) and the instruction files (`CLAUDE.md` / `AGENTS.md`), interviewing only for facts the repo can't reveal.
- **[setup-dividedby-skills](./skills/config/setup-dividedby-skills/SKILL.md)** — Install the dividedby conventions — size labels, intake/idea-inbox, branching policy, the Conventions block, and HITL verification gates. Every network mutation is gated behind an explicit confirm step. Manual/slash invocation only.
- **[triage](./skills/config/triage/SKILL.md)** — Move issues through a state machine on our label vocabulary: show what needs attention, triage a specific issue with the appropriate outcome comment, and apply the outcome.
- **[workflow-onboarding](./skills/config/workflow-onboarding/SKILL.md)** — Install the loop-specific surface (LOOP/NETWORK labels + installed-skills snapshot) on a repo being onboarded into a proposal loop; runs after setup-dividedby-skills, every mutation gated behind explicit confirmation.

## Proposal loops

Scheduled workflows that propose improvements via labeled issues (a human decides — never auto-applied) — `improve-codebase-architecture`, `staleness-review`, and `changelog-health`. Onboarding docs for standing them up in other repos:

- **[proposal-loop-harness](./docs/onboarding/proposal-loop-harness.md)** — the shared skeleton the loops follow (propose-via-issues, scheduling; two vendor a fetch-fresh skill install, `changelog-health` is centralized and host-only).
- **[arch-review-setup](./docs/onboarding/arch-review-setup.md)** — the simpler `improve-codebase-architecture` loop (codebase → refactor proposals).
- **[staleness-setup](./docs/onboarding/staleness-setup.md)** — the monthly `staleness-review` loop (toolchain pins → ranked staleness report, complementing Dependabot).

## Docs

- [CHANGELOG](./CHANGELOG.md) — notable changes by release
- [CODING_STANDARDS](./CODING_STANDARDS.md) — markdown skill and harness Python conventions

## Upstream

These skills soft-depend on two upstream catalogs, expected to be installed
alongside this plugin: `mattpocock/skills` and the
`anthropics/claude-plugins-official` marketplace.

**From `mattpocock/skills`:**

**Workflow:** `grill-with-docs`, `to-spec` / `to-tickets` / `tdd`,
`improve-codebase-architecture`, `code-review`

**From `anthropics/claude-plugins-official`:** `typescript-lsp`, `pyright-lsp`

See [`CONTEXT.md`](./CONTEXT.md) and [ADR 0024](./docs/adr/0024-lean-on-upstream-skills-soft-depend-over-reinvent.md) for the authoritative contract (delete-and-soft-depend posture, thin-wrapper conditions, authoring standard).
