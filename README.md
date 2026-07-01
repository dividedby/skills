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
- **[flow-pr](./skills/engineering/flow-pr/SKILL.md)** — End-to-end flow-aware PR helper: reads the repo's default branch as the integration target, cuts a feature branch, commits → pushes → opens PR against the default branch, reviews and fixes the diff (via `/review`), gates on CI green, then merges. Promotion (default→main) is always-confirmed and only applies when the default branch is not main.
- **[frontend-design](./skills/engineering/frontend-design/SKILL.md)** — Design, refine, and audit production-grade frontend interfaces across React, Next.js, Tailwind, and vanilla HTML/CSS/JS that avoid generic AI aesthetics.
- **[repo-audit](./skills/engineering/repo-audit/SKILL.md)** — User-invoked audit that hunts high-leverage improvements in a repo (delete/lean, performance, architectural deepening, missing features) and produces a small set of epics with an ordered roadmap — reconciled against the existing backlog, not filed beside it.
- **[software-design](./skills/engineering/software-design/SKILL.md)** — Turns a PRD and published backlog into named modules, located seams, and a testing strategy that makes issues TDD-ready.
- **[staleness-audit](./skills/engineering/staleness-audit/SKILL.md)** — Audit a repo's pinned toolchain versions (Node, Python, Go, container and CI matrices) for staleness and emit a ranked report — safe in-major bumps auto-applied behind a verify gate, cross-major / EOL jumps stay recommendations; the complement to Dependabot's library bumps.
- **[write-well](./skills/engineering/write-well/SKILL.md)** — Draft and de-slop English prose to a defensible core and clean output; two entry points (draft, improve).

### Config

Setting up and auditing a project's Claude config — instruction files and the settings/hooks harness. See the [bucket README](./skills/config/README.md) for the internal seams.

- **[project-claude-config](./skills/config/project-claude-config/SKILL.md)** — One state-routed pass over a project's Claude config: scaffold what's missing and critique what's present across both the harness (`.claude/settings.json`) and the instruction files (`CLAUDE.md` / `AGENTS.md`), interviewing only for facts the repo can't reveal.
- **[setup-dividedby-skills](./skills/config/setup-dividedby-skills/SKILL.md)** — Install the dividedby conventions on top of setup-matt-pocock-skills — size labels, intake/idea-inbox, branching policy, the Conventions block, and HITL verification gates. Every network mutation is gated behind an explicit confirm step. Manual/slash invocation only.
- **[triage](./skills/config/triage/SKILL.md)** — Move issues through a state machine on our label vocabulary: show what needs attention, triage a specific issue with the appropriate outcome comment, and route skill-request issues through the ADR-0021 prior-art scan.
- **[workflow-onboarding](./skills/config/workflow-onboarding/SKILL.md)** — Install the loop-specific surface (LOOP/NETWORK labels + installed-skills snapshot) on a repo being onboarded into a proposal loop; runs after setup-dividedby-skills, every mutation gated behind explicit confirmation.

### Meta

- **[apply-agent-research](./skills/meta/apply-agent-research/SKILL.md)** — Apply an external agent-research knowledge base to a repo's own agent-meta: read a public knowledge mirror plus the repo's own governance docs, then propose its single best improvement (at most one per run, clearing a high independent bar) as a labeled issue — never editing, committing, or merging.
- **[skill-divergence-audit](./skills/meta/skill-divergence-audit/SKILL.md)** — Recurring, report-only audit that diffs this repo's published skills against Matt Pocock's repo and the agent-research KB, classifies each gap, and proposes its single best realignment issue — at most one per run, never editing, committing, or merging.

## Proposal loops

Scheduled, skill-driven workflows that propose improvements via labeled issues (a human decides — never auto-applied). Onboarding docs for standing them up in other repos:

- **[proposal-loop-harness](./docs/onboarding/proposal-loop-harness.md)** — the shared skeleton both loops follow (fetch-fresh skill install, propose-via-issues, scheduling).
- **[consumer-setup](./docs/onboarding/consumer-setup.md)** — wire a repo up as an `apply-agent-research` Consumer (agent-meta self-improvement + the cross-repo `skill-request` / `skill-promotion` channels).
- **[arch-review-setup](./docs/onboarding/arch-review-setup.md)** — the simpler `improve-codebase-architecture` loop (codebase → refactor proposals).

## Docs

- [CHANGELOG](./CHANGELOG.md) — notable changes by release
- [CODING_STANDARDS](./CODING_STANDARDS.md) — markdown skill and harness Python conventions

## Upstream

These skills soft-depend on `mattpocock/skills` — install it alongside this plugin.
The following skills are expected to be present from that suite:

**Foundation:** `codebase-design`, `domain-modeling`, `writing-great-skills`

**Workflow:** `diagnosing-bugs`, `prototype`, `to-prd` / `to-issues` / `tdd` /
`implement`, `grilling` / `grill-with-docs`

See [`CONTEXT.md`](./CONTEXT.md) and [ADR 0024](./docs/adr/0024-lean-on-upstream-skills-soft-depend-over-reinvent.md) for the authoritative contract (delete-and-soft-depend posture, thin-wrapper conditions, authoring standard).
