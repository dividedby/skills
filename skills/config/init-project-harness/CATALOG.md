# Project Harness Catalog

Shared reference for `init-project-harness` and `audit-project-harness`. Every recommendation must come from this catalog, be **fact-gated** (only proposed when the repo actually triggers it), and pass the **annoyance filter**. Validate the exact keys/events you propose against current docs before showing the user (see SKILL.md Step "Validate").

Canonical docs (anchors for validation):
- Hooks: https://code.claude.com/docs/en/hooks
- Settings: https://code.claude.com/docs/en/settings
- Permissions: https://code.claude.com/docs/en/permissions

## Annoyance filter — propose a hook ONLY if all four hold
1. **Triggered by a real detected fact** (a tool/file/command that actually exists in the repo).
2. **Deterministic / non-interactive** (no prompts, no nagging).
3. **Fast & well-placed** — PostToolUse on Edit/Write, or Stop; never a blocking gate on *every* Bash call. A **narrow** PreToolUse matcher that fires only on a specific dangerous command class (e.g. the git guard below) is the one exception, and only when the CI/AFK carve-out applies.
4. **Earns its place** — either replaces a CLAUDE.md instruction (turning "remember to X" into automatic enforcement) or closes a concrete risk.

## Verified harness facts (bake into reasoning)
- **Hooks are additive across scopes** — a project hook never replaces a global one, it adds. So re-declaring a global hook makes it fire twice (→ `cut`), and the global safety hooks (`read-guard`, `bash-guard`) cannot be weakened from project config. No dedup is documented; treat duplication as real waste.
- **CI/AFK carve-out to the no-re-declare rule** ([ADR 0013](../../../docs/adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md)) — the rule above assumes the global harness *travels with every run*. It doesn't: an AFK/CI run of `claude -p` has no `~/.claude/`, so the global `bash-guard` git protections are absent. A project-scope **guard hook** that must fire in that context is **not** duplication — it is the only copy that runs. On a developer's machine the double-fire is redundant-but-harmless (same exit-2 block, one extra log line), so re-declaring is correct, not a `cut`. Detect the context by proxy, not by introspecting whether a global twin will fire.
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
| **PreToolUse git guard** on `Bash` | Repo runs agents where the global `bash-guard` is **absent** — detected by proxy: a CI workflow invoking `claude -p` / an agent runner, **or** an existing project-scope guard hook (e.g. a `pnpm-guard`). See the CI/AFK carve-out above. | Blocks (exit 2) destructive git: `push --force`/`-f`, `reset --hard`, branch deletion (`branch -D`/`-d`, `push --delete`, `push :branch`), `clean -f`/`-fd`/`-x`, worktree-discarding `checkout`/`restore`. **Passes** add/commit/status/fetch/pull, branch-switch `checkout <branch>`, `--force-with-lease`/`--force-if-includes`, soft/mixed reset. The non-obvious exclusions are the point — they keep the guard usable so agents don't route around it. | Low — narrow matcher on git only, not a gate on every Bash call; redundant-but-harmless where a global guard is present |
| **`env` project vars** | Project needs a consistent non-secret env across sessions (e.g. `NODE_ENV`, a test-mode flag) | Stable env without per-session setup | Zero — **never** put secrets here |
| **`enabledPlugins` (light)** | Repo language clearly matches an available plugin (e.g. a TS repo + a TS LSP plugin) and it isn't already on | Better tooling for that stack | Low — don't churn; merge behavior is undocumented, so confirm and recommend cautiously |

**Git-guard matcher — two boundary traps the pattern must get right:**
- `checkout`/`restore` are **overloaded**: `git checkout main` (safe branch switch) vs `git checkout -- <pathspec>` / `git checkout .` / `checkout -f` (discards worktree). Distinguish by the presence of `--`/pathspec/`-f`; never block `checkout`/`restore` wholesale.
- `--force-with-lease`/`--force-if-includes` must **survive** — a substring match on `--force` wrongly catches them. Use word-boundary / explicit-exclusion logic.

## Anti-catalog — considered and rejected (always surface these with the reason)
- **Notification / Stop sounds / desktop pings** — pure annoyance, no project value.
- **Blocking PreToolUse gates on every `Bash` call** — duplicates/competes with the global `bash-guard`, slows every command. (A **narrow** matcher scoped to one dangerous command class — the git guard above — is not this; it gates only matching commands and is justified by the CI/AFK carve-out.)
- **Re-adding a `permissions.allow` list** — banned; the global bypass-mode + surgical hooks are the backstop.
- **Re-declaring the global safety hooks** (`read-guard`/`bash-guard`) **verbatim** — additive, so they'd fire twice for no gain. (Exception: a narrow guard that must run where global config is absent — see the CI/AFK carve-out and the git guard above. That isn't re-declaring the global hook verbatim; it's the only copy that runs in CI.)
- **Auto-commit / auto-push / auto-deploy on `Stop`** — surprising and hard to reverse; outward-facing actions need a human.
- **Overriding scalar globals** (`model`, `defaultMode`, `effortLevel`, statusline, notif flags) in a project file — personal/global preferences; a project override is a contradiction to flag, not an addition.
