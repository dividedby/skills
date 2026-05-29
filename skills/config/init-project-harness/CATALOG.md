# Project Harness Catalog

Shared reference for `init-project-harness` and `audit-project-harness`. Every recommendation must come from this catalog, be **fact-gated** (only proposed when the repo actually triggers it), and pass the **annoyance filter**. Validate the exact keys/events you propose against current docs before showing the user (see SKILL.md Step "Validate").

Canonical docs (anchors for validation):
- Hooks: https://code.claude.com/docs/en/hooks
- Settings: https://code.claude.com/docs/en/settings
- Permissions: https://code.claude.com/docs/en/permissions

## Annoyance filter — propose a hook ONLY if all four hold
1. **Triggered by a real detected fact** (a tool/file/command that actually exists in the repo).
2. **Deterministic / non-interactive** (no prompts, no nagging).
3. **Fast & well-placed** — PostToolUse on Edit/Write, or Stop; never a blocking gate on every Bash call.
4. **Earns its place** — either replaces a CLAUDE.md instruction (turning "remember to X" into automatic enforcement) or closes a concrete risk.

## Verified harness facts (bake into reasoning)
- **Hooks are additive across scopes** — a project hook never replaces a global one, it adds. So re-declaring a global hook makes it fire twice (→ `cut`), and the global safety hooks (`read-guard`, `bash-guard`) cannot be weakened from project config. No dedup is documented; treat duplication as real waste.
- **`deny` permissions union and win from any scope, un-overridable** → project `deny` rules are robust. (Allowlists stay banned — global safety architecture.)
- **`env`/scalars: most-specific wins.** Plugin merge is undocumented → recommend cautiously.
- **Project settings load root-only.** A nested `packages/*/.claude/settings.json` is NOT loaded → flag as dead config.

## Catalog (propose only when trigger matches)

| Hook / setting | Trigger | Value | Annoyance |
|---|---|---|---|
| **PostToolUse formatter** on `Edit`/`Write` | Repo has a configured formatter (prettier, black, ruff format, gofmt, rustfmt) **and** no formatter hook exists | Auto-formats the edited file; lets CLAUDE.md drop any "run the formatter" line | Near-zero — runs once after an edit, scoped to the changed file |
| **PostToolUse typecheck** on `Stop` | A **fast** typecheck/lint command exists (`tsc --noEmit`, `mypy`, `ruff check`) | Surfaces errors at end of turn instead of next session | Low — only if fast; **exclude** if it runs the full test suite or takes more than a few seconds |
| **`deny` secret reads** | Secret files present (`.env*`, `*.pem`, `id_rsa`, `credentials/`, `secrets/`) **and** the global `read-guard` does not already cover them | Blocks the agent from reading project secrets | Zero — only the delta beyond what `read-guard` already blocks |
| **`deny` destructive ops on data** | A clear irreplaceable-data dir exists (`data/`, `migrations/`, `fixtures/`, a local db file) | Blocks `rm`/overwrite of data the project can't regenerate | Zero — narrowly scoped deny |
| **`env` project vars** | Project needs a consistent non-secret env across sessions (e.g. `NODE_ENV`, a test-mode flag) | Stable env without per-session setup | Zero — **never** put secrets here |
| **`enabledPlugins` (light)** | Repo language clearly matches an available plugin (e.g. a TS repo + a TS LSP plugin) and it isn't already on | Better tooling for that stack | Low — don't churn; merge behavior is undocumented, so confirm and recommend cautiously |

## Anti-catalog — considered and rejected (always surface these with the reason)
- **Notification / Stop sounds / desktop pings** — pure annoyance, no project value.
- **Blocking PreToolUse gates on every `Bash` call** — duplicates/competes with the global `bash-guard`, slows every command.
- **Re-adding a `permissions.allow` list** — banned; the global bypass-mode + surgical hooks are the backstop.
- **Re-declaring the global safety hooks** (`read-guard`/`bash-guard`) — additive, so they'd fire twice for no gain.
- **Auto-commit / auto-push / auto-deploy on `Stop`** — surprising and hard to reverse; outward-facing actions need a human.
- **Overriding scalar globals** (`model`, `defaultMode`, `effortLevel`, statusline, notif flags) in a project file — personal/global preferences; a project override is a contradiction to flag, not an addition.
