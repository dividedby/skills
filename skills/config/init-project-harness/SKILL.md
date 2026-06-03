---
name: init-project-harness
description: Scaffold a repo's project harness (.claude/settings.json) — propose practical, fact-gated hooks, deny-only permissions, and env the "earn the line" way, without duplicating or weakening the global config. The additive counterpart to audit-project-harness; run before init-project-claude. Manual/slash invocation only.
disable-model-invocation: true
---

# Project Harness Init

Scaffold this project's **harness** — `.claude/settings.json` (hooks, `env`, deny-only permissions, light plugins) — when it doesn't yet exist. The **additive** counterpart to `audit-project-harness` (subtractive). Run this **before** `/init-project-claude`: a hook that enforces something automatically beats a CLAUDE.md line asking the agent to remember it, so settling the harness first lets the instruction pass stay lean. Propose before writing; nothing is written until approved.

Be efficient: **delegate discovery to an Explore subagent** and work from condensed findings + `file:line`. Don't pull whole files into the parent.

## Step 1 — Global baseline
Read `~/.claude/settings.json` and the two safety hooks (`read-guard.py`, `bash-guard.py`) once. Treat the global harness (bypass-style `defaultMode`, the surgical PreToolUse hooks, model/effort/statusline, enabled plugins) as **already in effect**. Nothing you scaffold may restate, duplicate, or weaken any of it. Hooks are **additive across scopes** — re-declaring a global hook makes it fire twice, and the safety hooks cannot be weakened from here. **Carve-out:** this assumes the global harness travels with every run; it doesn't. For a **guard hook** that must fire where global config is absent (an AFK/CI `claude -p` run — no `~/.claude/`), project-scope re-declaration is correct, not duplication, since it is the only copy that runs ([ADR 0013](../../../docs/adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md); see the git guard in CATALOG.md).

## Step 2 — Detect (subagent)
Dispatch Explore to report:
- Whether `.claude/settings.json` already exists with real harness content. Also note any `.claude/settings.local.json` (read-only — see Step 4).
- **Fact triggers** for the catalog: configured formatter, fast typecheck/lint command, secret files (`.env*`, `*.pem`, `credentials/`), irreplaceable-data dirs (`data/`, `migrations/`), language/stack, package manager.

**If substantive harness config already exists, stop** and point the user at `/audit-project-harness` — this skill is for greenfield scaffolding, not critique.

**Note (root-only):** project settings load only from the repo-root `.claude/`. There is no per-package settings file; do not scaffold nested ones.

## Step 3 — Propose (from the catalog)
Read [CATALOG.md](CATALOG.md). Propose **only** entries whose trigger matched in Step 2 and that pass the 4-part annoyance filter. For each: what it does, why it earns its place, and its annoyance cost. Then list catalog/anti-catalog entries you **deliberately rejected** and why (no trigger, or filtered out). Recommend `deny`-only for permissions — **never** an allowlist.

## Step 4 — Validate against current docs
Before showing the proposal, **WebFetch the catalog's canonical doc anchors** (Hooks + Settings, plus Permissions if a permission is proposed) to confirm the **specific** hook events, matchers, and settings keys you're proposing are current, supported, and non-deprecated. Drop or correct anything stale. Scope the check to what you're actually proposing — don't validate the whole catalog. (Skip this step if Step 2 hit the stop-condition and nothing is proposed.)

## Step 5 — Output & approval
Show the proposed `settings.json` additions and a one-line summary of each. Await approval. **Route the actual write through the `update-config` skill** — don't hand-edit JSON here. Write to the shared `settings.json`, never `settings.local.json`.

## Step 6 — Hand off
End with a pointer: run `/init-project-claude` next to scaffold instruction files (skipping anything these hooks now enforce). If any proposal involved a real judgment call (a hook's annoyance vs. value, which `deny` rules), offer `/grill-me` to drill in before deciding.
