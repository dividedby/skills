---
name: init-project-claude
description: Scaffold a repo's missing agent-instruction files (CLAUDE.md / AGENTS.md) and propose project harness config (.claude/settings.json hooks) the "earn the line" way. The additive counterpart to audit-project-claude. Manual/slash invocation only.
disable-model-invocation: true
---

# Project CLAUDE.md Init

Scaffold this project's agent-instruction files and harness config when they don't yet exist. This is the **additive** counterpart to `audit-project-claude` (which is subtractive — it critiques files that already exist). Same bar applies: **every line in a CLAUDE.md loads into every session**, so only earn-the-line facts go in. Propose before writing; don't create files until approved.

Be efficient: **delegate discovery to an Explore subagent** and work from its condensed findings + `file:line` refs. Don't pull whole files into the parent context.

## Step 1 — Global baseline
Read `~/.claude/CLAUDE.md` once. Treat everything in it (communication style, "read first", code-style defaults, discuss-before-implementing, backpressure/verification, the safety hooks) as ALREADY IN EFFECT. Nothing you scaffold may restate or weaken any of it.

## Step 2 — Detect (subagent)
Dispatch Explore to report:
- Which of `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json` already exist (root + nested).
- Monorepo layout (workspaces / packages / apps), if any.
- Build·test·lint·format tooling, package manager, language(s) — from manifests (`package.json`, `pyproject.toml`, `Makefile`, `justfile`, CI config, etc.) and README.

**If the substantive files already exist, stop** and point the user at `/audit-project-claude` instead — this skill is for greenfield scaffolding, not critique.

## Step 3 — Scaffold CLAUDE.md / AGENTS.md (if missing)
CLAUDE.md is an **index, not a manual**. Include only facts that (a) are project-specific, (b) change behavior, and (c) are NOT derivable from a quick read of code/README/manifests but are tedious to rediscover each session. Typical keepers:
- Build / test / lint / run commands (the exact incantations).
- A short architecture map — where the important things live.
- Pointers (by path) to domain docs, conventions, or workflows that live elsewhere; load on demand, don't inline.
- Conventions that **differ** from sensible defaults.

Do NOT restate global preferences, generic best practices, or anything `/init` would boilerplate. Keep long content out of the file — leave a one-line pointer to a linked doc. **Don't scaffold an instruction a hook already enforces:** since `/init-project-harness` runs first, if a PostToolUse formatter or test-on-Stop hook now exists, omit the matching "remember to..." line — the hook is automatic and costs zero context.

**Monorepo:** short root file (cross-cutting only — repo layout, how to find the right app, shared tooling) + per-app files (that app's specifics; inherits global + root, so no repetition).

## Step 4 — Harness config is out of scope
Hooks and `.claude/settings.json` are owned by **`/init-project-harness`** (and `/audit-project-harness`) — run that **first**, so this pass can skip any instruction a hook now enforces. Don't propose settings/hooks here.

## Step 5 — Output & approval
Show the proposed file(s) and a one-line summary of each addition. Await approval before writing.

After scaffolding, `/audit-project-claude` is the natural follow-up pass once the files have accreted content. For domain glossary (`CONTEXT.md`) and architecture decision records (`docs/adr/`), see `grill-with-docs` — this skill intentionally does not scaffold those.
