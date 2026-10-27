# Skills

My personal Claude Code skills.

## Install

```bash
pnpm dlx skills@latest add dividedby/skills
```

Pick the skills you want when prompted. Re-run to update.

## Skills

### Engineering

- **[council](./skills/engineering/council/SKILL.md)** — Convene a blind, diverse multi-persona panel (Falsifier, Minimalist, Pragmatist + conditional seats) that returns a synthesized second opinion plus the dissent the chair did not adopt; one blind parallel round plus a chair synthesis on the built-in Workflow tool.
- **[repo-audit](./skills/engineering/repo-audit/SKILL.md)** — Read-only audit of a repo's code, design, repo hygiene and docs, and market: parallel lens agents, every high finding verified at its source, published as one private report page with screenshots, mockups and a Now/Next/Later plan.

## Docs

- [CHANGELOG](./CHANGELOG.md) — notable changes by release
- [CODING_STANDARDS](./CODING_STANDARDS.md) — markdown skill conventions

## Upstream

These skills soft-depend on two upstream catalogs, expected to be installed
alongside this plugin: `mattpocock/skills` and the
`anthropics/claude-plugins-official` marketplace.

**From `mattpocock/skills`:**

**Workflow:** `grill-with-docs`, `to-spec` / `to-tickets` / `tdd`,
`improve-codebase-architecture`, `code-review`

**From `anthropics/claude-plugins-official`:** `typescript-lsp`, `pyright-lsp`

See [`CONTEXT.md`](./CONTEXT.md) and [ADR 0024](./docs/adr/0024-lean-on-upstream-skills-soft-depend-over-reinvent.md) for the authoritative contract (delete-and-soft-depend posture, thin-wrapper conditions, authoring standard).
