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
- **[context-firewall](./skills/engineering/context-firewall/SKILL.md)** — Restructure a long, multi-item run so late items don't decay: a fresh discarded sub-agent context per item, between-item budget checkpoints, and intentional compaction. Loop optional.
- **[flow-pr](./skills/engineering/flow-pr/SKILL.md)** — End-to-end flow-aware PR helper: reads the repo's default branch as the integration target, cuts a feature branch, commits → pushes → opens PR against the default branch, reviews and fixes the diff (via `/review`), gates on CI green, then merges. Promotion (default→main) is always-confirmed and only applies when the default branch is not main.
- **[frontend-design](./skills/engineering/frontend-design/SKILL.md)** — Design, refine, and audit production-grade frontend interfaces across React, Next.js, Tailwind, and vanilla HTML/CSS/JS that avoid generic AI aesthetics.
- **[software-design](./skills/engineering/software-design/SKILL.md)** — Turns a PRD and published backlog into named modules, located seams, and a testing strategy that makes issues TDD-ready.
- **[staleness-audit](./skills/engineering/staleness-audit/SKILL.md)** — Audit a repo's pinned toolchain versions (Node now; wider ecosystem later) for staleness and emit a ranked, recommend-only report — the complement to Dependabot's library bumps.

### Config

Setting up and auditing a project's Claude config — instruction files and the settings/hooks harness. See the [bucket README](./skills/config/README.md) for the internal seams.

- **[project-claude-config](./skills/config/project-claude-config/SKILL.md)** — One state-routed pass over a project's Claude config: scaffold what's missing and critique what's present across both the harness (`.claude/settings.json`) and the instruction files (`CLAUDE.md` / `AGENTS.md`), interviewing only for facts the repo can't reveal.

### Meta

- **[apply-agent-research](./skills/meta/apply-agent-research/SKILL.md)** — Apply an external agent-research knowledge base to a repo's own agent-meta: read a public knowledge mirror plus the repo's own governance docs, then propose its few best improvements (at most five per run, each clearing a high independent bar) as labeled issues — never editing, committing, or merging.

## Proposal loops

Scheduled, skill-driven workflows that propose improvements via labeled issues (a human decides — never auto-applied). Onboarding docs for standing them up in other repos:

- **[proposal-loop-harness](./docs/onboarding/proposal-loop-harness.md)** — the shared skeleton both loops follow (fetch-fresh skill install, propose-via-issues, scheduling).
- **[consumer-setup](./docs/onboarding/consumer-setup.md)** — wire a repo up as an `apply-agent-research` Consumer (agent-meta self-improvement + the cross-repo `skill-request` / `skill-promotion` channels).
- **[arch-review-setup](./docs/onboarding/arch-review-setup.md)** — the simpler `improve-codebase-architecture` loop (codebase → refactor proposals).
