# Audit posture (subtractive)

Applied to whatever the detect pass found **present with real content**. The goal is a lean, safe config: minimal startup context on the instructions side, a harness that adds real project value without duplicating or weakening the global. Output a concise finding list — don't edit until the batch is approved.

## Verbs

Every finding uses one of these, with a ref (`settings.json` key-path or `file:line`) and a one-line why:

- **`cut`** — duplication of the global (a re-declared safety hook now firing twice; a CLAUDE.md line restating a global preference or a generic best practice) or anything providing no project value.
- **`fix-contradiction`** — conflicts with the global: a re-added `permissions.allow` list, a scalar override (`model`, `defaultMode`, `effortLevel`, statusline, notif flags), a different commit identity, "skip tests", any attempt to weaken the safety architecture. **Surface and ask — don't silently resolve.**
- **`flag`** — a `settings.local.json` override that shadows/contradicts the shared file; stray nested `.claude/settings.json` (dead config — root-only loading); a CLAUDE.md pointer whose target isn't loadable (wiki, Notion, code comment, non-markdown).
- **`move-to-<doc>`** — inline bloat in an instruction file (workflows, glossaries, API docs) that belongs in a linked doc with a one-line pointer left behind. Name the destination.
- **`add`** — a high-value catalog entry whose trigger matched but which is missing (harness: passes the annoyance filter; instructions: passes the earn-the-line filter).
- **`keep`** — earns its place: project-specific, changes behavior, non-duplicative — and, for a hook, still passing the annoyance filter (deterministic, non-interactive, fast). An existing hook that nags or blocks broadly fails `keep` even if it duplicates nothing.

## Harness checks

Against [CATALOG.md](CATALOG.md) "Harness" — the verified facts, catalog triggers, and anti-catalog:

- Re-declared global hooks → `cut` (additive scopes; fires twice) — **except** (a) under the CI/AFK guard carve-out (must run where global config is absent) or (b) the repo ships `.claude/hooks/<name>.py` and the global guard yields via namesake-defer — both defined in the catalog's Verified harness facts.
- Heredoc commit bodies (i.e. `git commit -m "$(cat <<'EOF'...)"`) → `fix-contradiction` — blocked by `git-guard`; the fix is `git commit -F <file>`.
- Permissions: `deny`-only is the rule; any `allow` list → `fix-contradiction`.
- Missing triggered catalog hooks → `add`.

## Instruction-file checks

Against [CATALOG.md](CATALOG.md) "Instructions" — the earn-the-line filter, line classes, and anti-catalog:

- **Prefer enforcement over instruction.** Cut any line a hook (global or project) already enforces deterministically. Since the harness concern ran first, you know exactly what's enforced.
- **Progressive disclosure.** CLAUDE.md is an index, not a manual; long content moves out behind a pointer — and the pointer only earns its place if the target is clean, loadable, in-repo markdown.
- **Monorepo split** per the catalog's line class: flag facts duplicated between root and an app file, or app-specific facts that leaked into root.

## Label-doc drift check (cross-seam — detect only)

Run this check as part of Step 2 (Detect). It is **not** a harness or instruction finding — it is a seam-boundary report that blocks the all-clear if triggered.

### What to look for in the target repo's `docs/agents/`

A well-formed repo has exactly `docs/agents/triage-labels.md` containing the dividedby CORE/LOOP-NETWORK/CHANNELS tiering structure (seeded from `dividedby/skills docs/agents/labels.md`).

Drift shapes to detect:

| Shape | What you see | Verdict |
|---|---|---|
| Stray `labels.md` | `docs/agents/labels.md` exists (the `dividedby/skills` source file, not the target-repo convention file) | drifted |
| Short-form/pointer `triage-labels.md` | `docs/agents/triage-labels.md` exists but does not contain the CORE/LOOP-NETWORK/CHANNELS tiering structure — e.g. it is Matt's version (`needs-info`, Matt-specific role→label wording), a stub, or a pointer | drifted |
| `labels.md`-only repo | `docs/agents/labels.md` exists but `docs/agents/triage-labels.md` does not | drifted |
| No label doc at all | Neither file exists | drifted |
| Correct | `docs/agents/triage-labels.md` exists and contains the dividedby tiering structure; no stray `labels.md` | clear |

### On drift: flag and hand off — do not fix

If any drift shape is detected, **do not edit or normalize the label doc**. That surface is owned by `setup-dividedby-skills`. Instead, surface a `flag` finding:

> **`flag` — labels drifted — run `setup-dividedby-skills`** (`docs/agents/` label-doc shape does not match the dividedby convention; `setup-dividedby-skills` owns the fix — see [ADR 0023](../../../docs/adr/0023-setup-dividedby-skills-vs-project-claude-config-seam.md))

Include the drift shape (which of the four patterns above you saw). This finding goes into the output batch and **prevents a whole-repo all-clear** — the harness/instructions may be fine, but the label-doc surface is not cleared here.

If the label-doc is clean, note it briefly in the output ("label-doc: `triage-labels.md` present, dividedby content — clear") and move on. Do not detail the label contents further — that is `setup-dividedby-skills`' job.

## Output

Per file/concern: the verb list with refs, then the proposed lean structure (trimmed tree + headers for instruction files; proposed key structure for the harness). Feeds the single batch approval in SKILL.md's final step.

For the label-doc check: include the finding (flag or clear) in the output. If flagged, the report must explicitly state that the all-clear covers only harness/instructions — label-doc drift remains open for `setup-dividedby-skills` to resolve.
