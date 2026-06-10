---
name: project-claude-config
description: Get a project's Claude config right in one state-routed pass — scaffold what's missing and critique what's present across both the harness (.claude/settings.json hooks, deny-only permissions, env) and the instruction files (CLAUDE.md / AGENTS.md), interviewing only for facts the repo can't reveal. Use for greenfield setup, auditing an established repo, or the common partial case (some config exists, some doesn't). Manual/slash invocation only.
disable-model-invocation: true
---

# Project Claude Config

One pass that gets this project's Claude config right. **The skill routes by repo state, not by a mode you pick:** for each concern it finds missing, it scaffolds (additive posture); for each it finds present, it critiques (subtractive posture) — both in the same run, so a repo with a `settings.json` but no `CLAUDE.md` gets each file the treatment it needs.

Two concerns, always in this order:

1. **Harness** — `.claude/settings.json` (hooks, `env`, deny-only permissions, light plugins). First, because a hook that enforces something automatically beats a CLAUDE.md line asking the agent to remember it.
2. **Instructions** — `CLAUDE.md` / `AGENTS.md`. Second, so this pass can skip or cut any line the harness now enforces.

One bar everywhere: **every line costs context or runs every session, so it must earn its place.** Nothing here restates or weakens the global `~/.claude/` config. Propose before writing; nothing is written until approved.

Be efficient: **delegate discovery to an Explore subagent** and work from condensed findings + `file:line` refs. Don't pull whole files into the parent context.

## Step 1 — Global baseline

Read `~/.claude/CLAUDE.md`, `~/.claude/settings.json`, and the two safety hooks (`read-guard.py`, `bash-guard.py`) once. Treat all of it as **already in effect** — communication style, code-style defaults, the bypass-style `defaultMode`, the surgical PreToolUse hooks, model/effort/statusline, enabled plugins. Nothing you scaffold or keep may restate, duplicate, or weaken any of it. Key harness facts: hooks are **additive across scopes** (a re-declared global hook fires twice; the safety hooks can't be weakened from project config); `deny` rules union and win from any scope; scalars/`env` resolve most-specific-wins. **Carve-out:** a guard hook that must fire where the global harness is absent (an AFK/CI `claude -p` run — no `~/.claude/`) is correct to re-declare at project scope ([ADR 0013](../../../docs/adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md); the git guard in [CATALOG.md](CATALOG.md) is the worked example).

## Step 2 — Detect (subagent)

Dispatch Explore to report, without pulling full bodies into the parent:

- **What exists:** `.claude/settings.json` (root; note any `settings.local.json` — read-only, personal, outranks the shared file), any nested `packages/*/.claude/settings.json` (NOT loaded — dead config), and every `CLAUDE.md` / `AGENTS.md` (root + nested), with section headers and anything that looks long, duplicative, or derivable.
- **Fact triggers** for the catalog: configured formatter, fast typecheck/lint command, secret files (`.env*`, `*.pem`, `credentials/`), irreplaceable-data dirs (`data/`, `migrations/`), language/stack, package manager, CI workflows that run an agent headless.
- **Repo shape:** monorepo layout (workspaces/packages/apps), build·test·lint·run tooling from manifests and README.

## Step 3 — Route by state

From the detect report, assign each concern a posture:

- **Missing → scaffold** (additive). Follow [scaffold-stubs.md](scaffold-stubs.md): earn-the-line stubs built from repo facts, with a "here's what I inferred — confirm/correct" framing.
- **Present → audit** (subtractive). Follow [audit-checklist.md](audit-checklist.md): a concise `cut` / `move` / `keep` / `fix-contradiction` / `add` / `flag` list with `file:line` or key-path refs.

Run the harness concern fully (Steps 3–5) before the instructions concern, so the instructions pass knows what the hooks now enforce.

## Step 4 — Interview: gap-filler only, capped at the stub bar

The interview is **gated behind Explore** — never ask what the repo can answer. Ask only for facts the repo cannot reveal: what the project is for, intent and goals, conventions not yet visible in code, what the maintainer wants enforced. Cap it at the **stub bar**: enough to write earn-the-line stubs plus a confirm/correct summary — not config completeness. In practice this means the interview is heaviest on greenfield, near-silent on a mature repo (where questions are reserved for contradictions the audit surfaces).

## Step 5 — Propose from the catalog, validate, get approval

Every harness recommendation comes from [CATALOG.md](CATALOG.md): fact-gated (its trigger matched in Step 2) and past the annoyance filter; instruction-side keeps/cuts follow the catalog's instructions section. List catalog/anti-catalog entries you **deliberately rejected** and why. Recommend `deny`-only for permissions — never an allowlist.

Before showing the proposal, **WebFetch the catalog's canonical doc anchors** for whatever you're actually proposing (Hooks + Settings, plus Permissions or Memory as applicable) to confirm the specific events, matchers, and keys are current and non-deprecated. Scope the check to your proposal, not the whole catalog.

Then show everything as **one batch** — proposed `settings.json` changes, proposed/trimmed instruction files, each with a one-line why — and await approval. **Route settings writes through the `update-config` skill** (never hand-edit JSON, never write `settings.local.json`); write instruction files directly after approval.

If any item is a genuine judgment call (a hook's value vs. annoyance, a contradiction to resolve), offer `/grill-me`. For domain glossary (`CONTEXT.md`) and ADRs, point at `/grill-with-docs` — this skill does not scaffold those.
