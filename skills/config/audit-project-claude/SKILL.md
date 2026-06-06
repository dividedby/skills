---
name: audit-project-claude
description: Audit a project's CLAUDE.md / AGENTS.md files against the global config — cut duplication, flag contradictions, enforce progressive disclosure, and split monorepo root vs per-app instructions. Manual/slash invocation only.
disable-model-invocation: true
---

# Project CLAUDE.md Audit

Audit this project's agent-instruction files. **The goal is minimizing startup context** — every line in a CLAUDE.md loads into every session, so the bar is high. Output a concise cut / move / keep / fix-contradiction list with `file:line` refs. Do not edit until approved.

**Run `/audit-project-harness` first.** Knowing what the project's hooks enforce automatically lets this pass cut the instructions they make redundant (see Step 3, "Prefer enforcement over instruction").

Be efficient: don't read whole files into the parent context. **Delegate discovery and reading to an Explore subagent** and work from its condensed findings + `file:line` refs.

## Step 1 — Global baseline
Read `~/.claude/CLAUDE.md` once. Treat everything in it (communication style, "read first", code-style defaults, discuss-before-implementing, backpressure/verification, the safety hooks) as ALREADY IN EFFECT. Project files must not restate or weaken any of it.

## Step 2 — Locate (subagent)
Dispatch Explore to find every `CLAUDE.md` / `AGENTS.md` in the repo (root + nested) and return: the tree, plus each file's section headers and any inline content that looks long, duplicative, or derivable. Don't pull full file bodies into the parent — request excerpts only where a judgment call needs them.

If no such files exist, this skill has nothing to audit — point the user at `/init-project-claude` to scaffold them instead.

## Step 3 — Audit each file
- **No duplication of global.** Cut anything that repeats a global preference (tone, "match conventions", "verify after edits", safety rules).
- **No contradiction of global.** Flag conflicts (different commit identity, "skip tests", re-added permission lists, duplicated/broadened safety hooks). Surface and ask — don't silently resolve.
- **Earn the line.** Keep only if (a) project-specific, (b) changes behavior, (c) NOT derivable from code/README/manifests. Keepers: build/test/lint commands, architecture map, domain-vocab location, conventions that DIFFER from defaults.
- **Prefer enforcement over instruction.** Cut any instruction that a hook already enforces deterministically (global or project `.claude/settings.json`). E.g. if a PostToolUse formatter hook exists, drop "run the formatter after edits"; if a test-on-Stop hook exists, drop "always run tests." A hook is automatic and costs zero context; the line is dead weight.
- **Progressive disclosure.** CLAUDE.md is an index, not a manual. Long content (API docs, workflows, ADRs, glossaries) lives in linked files (`docs/`, `CONTEXT.md`, `docs/adr/`) referenced by path and loaded on demand. Recommend moving inline bloat out, leaving a one-line pointer. **The targets must be loadable too:** a pointer only earns its place if what it points to is clean, force-loadable markdown the agent can read without leaving the repo. Flag pointers whose targets are trapped in code comments, a wiki, an external tool (Notion/Confluence), or a non-markdown format — the index is only as good as the docs it indexes.

## Step 4 — Monorepo split (if applicable)
- **Root:** only cross-cutting facts — repo layout, how to find the right app, shared tooling, conventions common to all packages. Short.
- **Per-app:** only that app's specifics; it inherits global + root, so don't repeat them.
- Flag facts duplicated between root and an app file, or app-specific facts that leaked into root.

## Output
Per file: bullet list of `cut` / `move-to-<doc>` / `keep` / `fix-contradiction` with `file:line`. End with the proposed trimmed structure (tree + headers only). Await approval before editing.
