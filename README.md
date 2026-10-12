# Skills

My personal Claude Code skills.

## Install

```bash
pnpm dlx skills@latest add dividedby/skills
```

Pick the skills you want when prompted. Re-run to update.

## Skills

### Engineering

- **[council](./skills/engineering/council/SKILL.md)** — Convene a blind, diverse multi-persona panel (Falsifier, Minimalist, Pragmatist + conditional seats) that returns a synthesized second opinion plus the dissent the chair did not adopt; drives the built-in Workflow tool across three rounds.
- **[repo-audit](./skills/engineering/repo-audit/SKILL.md)** — User-invoked audit that hunts high-leverage improvements in a repo (delete/lean, performance, architectural deepening, missing features) and produces a small set of epics with an ordered roadmap — reconciled against the existing backlog, not filed beside it.

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
