---
name: project-claude-config
description: Scaffold and audit a project's Claude harness and instruction files in one state-routed pass. Manual/slash invocation only.
disable-model-invocation: true
---

# Project Claude Config

One pass that gets this project's Claude config right. **The skill routes by repo state, not by a mode you pick:** for each concern it finds missing, it scaffolds (additive posture); for each it finds present, it critiques (subtractive posture) — both in the same run, so a repo with a `settings.json` but no `CLAUDE.md` gets each file the treatment it needs.

Two concerns, always in this order:

1. **Harness** — `.claude/settings.json` (hooks, `env`, deny-only permissions, light plugins). First, because a hook that enforces something automatically beats a CLAUDE.md line asking the agent to remember it.
2. **Instructions** — `CLAUDE.md` / `AGENTS.md`. Second, so this pass can skip or cut any line the harness now enforces.

Every line costs context or runs every session — it must earn its place. Nothing scaffolded or kept may restate or weaken the global `~/.claude/` config. Propose before writing; nothing is written until approved.

Delegate discovery to an Explore subagent and work from condensed findings + `file:line` refs — don't pull whole files into the parent context (the one exception is in Step 2).

## Step 1 — Global baseline

Read `~/.claude/CLAUDE.md` and `~/.claude/settings.json` once. Treat all of it as **already in effect** — communication style, code-style defaults, the bypass-style `defaultMode`, the five PreToolUse global guards (read-guard, bash-guard, git-guard, secret-guard, typecheck-guard), model/effort/statusline, enabled plugins. Hook provenance lives in `~/repos/claude-config/hooks/README.md` — read that, not the `.py` files. The merge semantics (hooks additive across scopes, `deny` union, most-specific-wins scalars), the CI/AFK carve-out, and the namesake-defer rule live in [CATALOG.md](CATALOG.md) "Verified harness facts" — judge every hook against those facts, not from memory.

## Step 2 — Detect (subagent)

Dispatch Explore to report:

- **What exists.** For `.claude/settings.json` (root), return the **full content** — it is small and it is the audit object; key-path findings need the actual keys. Note any `settings.local.json` (read-only, personal, outranks the shared file) and any nested `packages/*/.claude/settings.json` (NOT loaded — dead config). For every `CLAUDE.md` / `AGENTS.md` (root + nested), return section headers plus anything that looks long, duplicative, or derivable — request excerpts only where a judgment call needs them, not full bodies.
- **Fact triggers** for the catalog: configured formatter, fast typecheck/lint command, secret files (`.env*`, `*.pem`, `credentials/`), irreplaceable-data dirs (`data/`, `migrations/`), language/stack, package manager, CI workflows that run an agent headless.
- **Repo shape:** monorepo layout (workspaces/packages/apps), build·test·lint·run tooling from manifests and README.
- **Label-doc shape:** check `docs/agents/` for the dividedby label-doc convention and report any drift — a stray `labels.md`, a short-form/pointer `triage-labels.md`, a `labels.md`-only repo, or no label doc at all. Detection only; the [audit-checklist.md](audit-checklist.md) "Lens 4" section defines the `flag` and the handoff to `setup-dividedby-skills` (ADR 0023). This skill never edits the label doc.

## Step 3 — Route by state

From the detect report, assign each concern a posture:

- **Missing or trivial → scaffold** (additive). An empty `{}` settings.json or an untouched boilerplate CLAUDE.md is greenfield, not audit material. Follow [scaffold-stubs.md](scaffold-stubs.md): earn-the-line stubs built from repo facts, with a "here's what I inferred — confirm/correct" framing.
- **Present with real content → audit** (subtractive). Follow [audit-checklist.md](audit-checklist.md): a concise finding list (`cut` / `move-to-<doc>` / `keep` / `fix-contradiction` / `add` / `gate` / `flag` — defined there) with `file:line` or key-path refs.

When either concern takes the **audit** posture, fan out to four independent config-critic lenses in `parallel()` — each reads the same Step 2 detect snapshot and produces its own finding list using the verbs in [audit-checklist.md](audit-checklist.md), without seeing the others' output:

1. **CLAUDE.md / instruction-budget** (Lens 1) — line-class audit, earn-the-line filter, startup-context load, monorepo split.
2. **Progressive-disclosure & `<important if>` gating** (Lens 2) — section sizing, pointer hygiene, situational-section gating. The `<important if>` gating check ([#399](https://github.com/dividedby/skills/issues/399)) runs here as-is; it is not re-implemented.
3. **Hooks & settings harness** (Lens 3) — hook re-declaration, permission posture, catalog trigger coverage, heredoc commit patterns.
4. **Skill-registration & label-doc drift** (Lens 4) — plugin/skill references in instruction files, label-doc drift detection and `setup-dividedby-skills` hand-off.

After all four return, a synthesis pass dedups overlapping findings and ranks the merged set by impact. That ranked set — not the individual lens outputs — feeds Steps 4 and 5. **The fan-out is internal: one interview (Step 4) and one approval batch (Step 5) cover both concerns; there is no second round-trip to the user.** Within the synthesis, harness findings (Lens 3) are settled before instruction findings (Lenses 1 and 2), so instruction proposals reflect what the harness would already enforce.

If the Workflow tool is unavailable or the fan-out fails, fall back to the single-pass sequential audit (today's behavior): run the [audit-checklist.md](audit-checklist.md) checks in order and note the fallback in the output.

### Illustrative workflow sketch

```
// ponytail: illustrative only — not a runnable literal script (ADR 0002)

const snapshot = detectReport;  // Step 2 output, shared across all lenses

const [lens1, lens2, lens3, lens4] = await parallel(
  agent("instruction-budget",  { input: snapshot }),
  agent("disclosure-gating",   { input: snapshot }),
  agent("hooks-harness",       { input: snapshot }),
  agent("skill-label-drift",   { input: snapshot }),
);

// Synthesis: dedup + rank; harness (lens3) settled before instructions (lens1, lens2)
const rankedFindings = await agent("synthesis", {
  input: { lens1, lens2, lens3, lens4 },
});

// rankedFindings feeds the single Step 4 interview and Step 5 proposal batch
```

## Step 4 — Interview: gap-filler only, capped at the stub bar

The interview is **gated behind Explore** — ask only for facts the repo cannot reveal: what the project is for, intent and goals, conventions not yet visible in code, what the maintainer wants enforced. Cap it at the **stub bar**: enough to write earn-the-line stubs plus a confirm/correct summary — not config completeness. In practice the interview is heaviest on greenfield and near-silent on a mature repo (where questions are reserved for contradictions the audit surfaces).

## Step 5 — Propose from the catalog, validate, get approval

The proposal is built from the ranked synthesis output of Step 3 — not from re-running the audit inline. Every harness recommendation comes from [CATALOG.md](CATALOG.md): fact-gated (its trigger matched in Step 2) and past the annoyance filter; instruction-side keeps/cuts follow the catalog's Instructions section. List catalog/anti-catalog entries you **deliberately rejected** and why. Recommend `deny`-only for permissions — never an allowlist.

Before showing the proposal, **WebFetch the catalog's canonical doc anchors for the harness items you're proposing** (Hooks + Settings, plus Permissions if a permission is proposed) to confirm the specific events, matchers, and keys are current and non-deprecated. Scope the check to your proposal, not the whole catalog; instruction-file proposals have no keys or events and need no fetch.

Then show everything as **one batch** — proposed `settings.json` changes, proposed/trimmed instruction files, each with a one-line why — and await approval. If the user rejects a hook that had justified omitting or cutting an instruction line, restore that line before writing. **Route settings writes through the `update-config` skill** (never hand-edit JSON, never write `settings.local.json`); write instruction files directly after approval.

If any item is a genuine judgment call (a hook's value vs. annoyance, a contradiction to resolve), offer `/grill-me`. For domain glossary (`CONTEXT.md`) and ADRs, point at `/grill-with-docs` — this skill does not scaffold those.
