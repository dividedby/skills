# Repo context — dividedby/skills

This is the **Repo-context include** for the architecture-review loop: the
per-repo half of the prompt, concatenated onto the fetched-fresh scope-free
skeleton (`harness/prompts/improve-codebase-architecture.md`) by the workflow
envelope. It carries what cannot be generalized — this repo's review scope and
the disciplines that bind it.

This file lives at `.github/arch-review-context.md` in this repo. It is one of
your in-repo files, so you **may** propose an edit to it (a human reviews before
merge) — unlike the upstream skeleton, which you may not.

## Scope

**Primary scope:** the `SKILL.md` files and their supporting markdown
under `skills/<bucket>/<name>/`. That is what this repo ships. Look
here first.

**Fallback scope (only if `skills/` is quiet):** if you cannot find a
high-confidence candidate inside `skills/`, you may expand to the
repo's meta-layer: `CLAUDE.md`, `CONTEXT.md`, `README.md`, files
under `docs/`, `.claude-plugin/plugin.json`, and the workflow files
under `.github/workflows/`. The same proposal rules apply: concrete
before/after, sources, no speculation. You may propose edits to the
workflow envelope or this Repo-context file — a human reviews before
merge.

**A worked example of over-reaching:** issue #12 is what "reaching for
something to file" looks like. If after checking both scopes nothing is
high-confidence, emit a `skipped` output and stop — a forced finding is
worse than no finding.

## Ecosystem context — read before proposing

The skills in this repo **extend** Matt Pocock's skills plugin at
<https://github.com/mattpocock/skills>. They are intended to be installed
alongside it, not as a replacement.

Before declaring any cross-reference broken, **read Matt's repo** (use
`WebFetch` on the GitHub URL or `gh api repos/mattpocock/skills/...`).
Skills you will find there include `grill-with-docs`, `to-prd`,
`to-issues`, `tdd`, `diagnose`, `triage`, `prototype`, `handoff`,
`write-a-skill`, `caveman`, `grill-me`, `improve-codebase-architecture`.

A link or reference like `../grill-with-docs/ADR-FORMAT.md` from inside
`skills/engineering/frontend-design/` is **not broken** — it points to
the sibling skill in Matt's plugin, which is co-installed at runtime.
Cross-plugin links rendering as broken on GitHub is the expected cost
of the extension pattern, not a defect.

You may only propose a `defect:` issue for a missing reference if you have
verified the target does not exist in either this repo **or**
mattpocock/skills.
