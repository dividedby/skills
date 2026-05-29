# Skills

My personal Claude Code skills.

## Install

```bash
npx skills@latest add dividedby/skills
```

Pick the skills you want when prompted. Re-run to update.

## Skills

### Engineering

- **[frontend-design](./skills/engineering/frontend-design/SKILL.md)** — Design, refine, and audit production-grade frontend interfaces across React, Next.js, Tailwind, and vanilla HTML/CSS/JS that avoid generic AI aesthetics.
- **[software-design](./skills/engineering/software-design/SKILL.md)** — Turns a PRD and published backlog into named modules, located seams, and a testing strategy that makes issues TDD-ready.

### Config

Setting up and auditing a project's Claude config — instruction files and the settings/hooks harness. See the [bucket README](./skills/config/README.md) for how the four fit together; run the harness pass before the instructions pass.

- **[init-project-harness](./skills/config/init-project-harness/SKILL.md)** — Scaffold a repo's `.claude/settings.json` with practical, fact-gated hooks, deny-only permissions, and env, without duplicating or weakening the global config.
- **[audit-project-harness](./skills/config/audit-project-harness/SKILL.md)** — Audit a repo's `.claude/settings.json` against the global config: cut redundant hooks, flag contradictions, recommend missing high-value hooks.
- **[init-project-claude](./skills/config/init-project-claude/SKILL.md)** — Scaffold missing `CLAUDE.md` / `AGENTS.md` instruction files the "earn the line" way.
- **[audit-project-claude](./skills/config/audit-project-claude/SKILL.md)** — Audit `CLAUDE.md` / `AGENTS.md` against the global config: cut duplication, flag contradictions, enforce progressive disclosure.
