# Skills

My personal Claude Code skills.

## Install

```bash
npx skills@latest add dividedby/skills
```

Pick the skills you want when prompted. Re-run to update.

## Skills

### Engineering

- **[autonomous-loop](./skills/engineering/autonomous-loop/SKILL.md)** — Take a briefed backlog to a safely-running unattended (AFK) agent loop: runtime selection, stop condition, per-iteration feedback gates, HITL→AFK graduation-by-guardrail with a cap, and monitor/stop/resume. Methodology, not a runtime.
- **[context-firewall](./skills/engineering/context-firewall/SKILL.md)** — Restructure a long, multi-item run so late items don't decay: a fresh discarded sub-agent context per item, between-item budget checkpoints, and intentional compaction. Loop optional.
- **[frontend-design](./skills/engineering/frontend-design/SKILL.md)** — Design, refine, and audit production-grade frontend interfaces across React, Next.js, Tailwind, and vanilla HTML/CSS/JS that avoid generic AI aesthetics.
- **[software-design](./skills/engineering/software-design/SKILL.md)** — Turns a PRD and published backlog into named modules, located seams, and a testing strategy that makes issues TDD-ready.

### Config

Setting up and auditing a project's Claude config — instruction files and the settings/hooks harness. See the [bucket README](./skills/config/README.md) for how the four fit together; run the harness pass before the instructions pass.

- **[init-project-harness](./skills/config/init-project-harness/SKILL.md)** — Scaffold a repo's `.claude/settings.json` with practical, fact-gated hooks, deny-only permissions, and env, without duplicating or weakening the global config.
- **[audit-project-harness](./skills/config/audit-project-harness/SKILL.md)** — Audit a repo's `.claude/settings.json` against the global config: cut redundant hooks, flag contradictions, recommend missing high-value hooks.
- **[init-project-claude](./skills/config/init-project-claude/SKILL.md)** — Scaffold missing `CLAUDE.md` / `AGENTS.md` instruction files the "earn the line" way.
- **[audit-project-claude](./skills/config/audit-project-claude/SKILL.md)** — Audit `CLAUDE.md` / `AGENTS.md` against the global config: cut duplication, flag contradictions, enforce progressive disclosure.

### Meta

- **[apply-agent-research](./skills/meta/apply-agent-research/SKILL.md)** — Apply an external agent-research knowledge base to a repo's own agent-meta: read a public knowledge mirror plus the repo's own governance docs, then propose at most one improvement per channel as a labeled issue — never editing, committing, or merging.

## Proposal loops

Scheduled, skill-driven workflows that propose improvements via labeled issues (a human decides — never auto-applied). Onboarding docs for standing them up in other repos:

- **[proposal-loop-harness](./docs/onboarding/proposal-loop-harness.md)** — the shared skeleton both loops follow (fetch-fresh skill install, propose-via-issues, scheduling).
- **[consumer-setup](./docs/onboarding/consumer-setup.md)** — wire a repo up as an `apply-agent-research` Consumer (agent-meta self-improvement + the cross-repo `skill-request` / `skill-promotion` channels).
- **[arch-review-setup](./docs/onboarding/arch-review-setup.md)** — the simpler `improve-codebase-architecture` loop (codebase → refactor proposals).
