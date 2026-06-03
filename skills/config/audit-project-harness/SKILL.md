---
name: audit-project-harness
description: Audit a project's harness (.claude/settings.json) against the global config — cut duplicated/redundant hooks, flag contradictions (re-added allowlists, scalar overrides, weakened safety), flag local-override shadowing, and recommend missing high-value hooks. The subtractive counterpart to init-project-harness; run before audit-project-claude. Manual/slash invocation only.
disable-model-invocation: true
---

# Project Harness Audit

Audit this project's **harness** — `.claude/settings.json` (hooks, `env`, permissions, plugins). **The goal is a lean, safe harness** that adds real project value without duplicating or weakening the global config. The subtractive counterpart to `init-project-harness`. Run this **before** `/audit-project-claude`: knowing what the harness enforces automatically lets you cut the CLAUDE.md instructions it makes redundant. Output a concise list with key-path refs; don't edit until approved.

Be efficient: **delegate discovery/reading to an Explore subagent** and work from condensed findings + refs. Don't pull whole files into the parent.

## Step 1 — Global baseline
Read `~/.claude/settings.json` and the two safety hooks (`read-guard.py`, `bash-guard.py`) once. Treat the global harness as **already in effect**. Key facts: hooks are **additive across scopes** (a re-declared global hook fires twice; safety hooks can't be weakened from project config); `deny` rules union and win from any scope; scalars/`env` resolve most-specific-wins. **Carve-out:** the additive rule assumes the global harness travels with every run; it doesn't. A **guard hook** that must fire where global config is absent (an AFK/CI `claude -p` run — no `~/.claude/`) is correct to re-declare at project scope, so don't `cut` it as duplication ([ADR 0013](../../../docs/adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md); the git guard in CATALOG.md is the worked example).

## Step 2 — Locate & read (subagent)
Dispatch Explore to return:
- The full `.claude/settings.json` content (root). If absent, **stop** and point the user at `/init-project-harness`.
- `.claude/settings.local.json` if present — **read-only**, for shadowing awareness (it's personal/gitignored and outranks the shared file).
- Any **nested** `packages/*/.claude/settings.json` — these are NOT loaded (root-only); flag as dead config.
- Fact triggers for "missing high-value hooks" (formatter, typecheck command, secret files, data dirs).

## Step 3 — Audit
Read the shared catalog at `~/.claude/skills/init-project-harness/CATALOG.md`. Produce a list using these verbs:
- **`cut`** — duplication of the global harness (a re-declared safety hook now firing twice; a hook the global already provides) or anything providing no project value.
- **`fix-contradiction`** — a re-added `permissions.allow` list, a scalar override (`model`, `defaultMode`, `effortLevel`, statusline, notif flags), or any attempt to weaken the safety architecture. **Surface and ask — don't silently resolve.**
- **`flag`** — a `settings.local.json` override that shadows/contradicts the shared file; stray nested settings files.
- **`add`** — a high-value catalog hook whose trigger matched but which is missing (passes the 4-part annoyance filter).
- **`keep`** — earns its place: project-specific, deterministic, non-duplicative.
Recommend `deny`-only for permissions; never propose an allowlist.

## Step 4 — Validate against current docs
Before showing `add` proposals (or any key you'd rewrite), **WebFetch the catalog's canonical doc anchors** (Hooks + Settings, plus Permissions if you're proposing a permission) to confirm the specific hook events, matchers, and settings keys are current, supported, and non-deprecated. Drop or correct anything stale. Scope to what you're touching. (Skip if Step 2 hit the stop-condition.)

## Step 5 — Output & approval
Per finding: `cut` / `fix-contradiction` / `flag` / `add` / `keep` with a `settings.json` key-path ref and a one-line why. End with the proposed lean structure. Await approval. **Route any write through the `update-config` skill** — write to the shared `settings.json`, never `settings.local.json`.

## Step 6 — Hand off
End with a pointer: run `/audit-project-claude` next to cut instructions these hooks make redundant. If any finding is a genuine judgment call (a hook's value vs. annoyance, a contradiction to resolve), offer `/grill-me` to drill in.
