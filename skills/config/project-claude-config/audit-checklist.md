# Audit posture (subtractive)

Applied to whatever the detect pass found **present**. The goal is a lean, safe config: minimal startup context on the instructions side, a harness that adds real project value without duplicating or weakening the global. Output a concise finding list — don't edit until the batch is approved.

## Verbs

Every finding uses one of these, with a ref (`settings.json` key-path or `file:line`) and a one-line why:

- **`cut`** — duplication of the global (a re-declared safety hook now firing twice; a CLAUDE.md line restating a global preference or a generic best practice) or anything providing no project value.
- **`fix-contradiction`** — conflicts with the global: a re-added `permissions.allow` list, a scalar override (`model`, `defaultMode`, `effortLevel`, statusline, notif flags), a different commit identity, "skip tests", any attempt to weaken the safety architecture. **Surface and ask — don't silently resolve.**
- **`flag`** — a `settings.local.json` override that shadows/contradicts the shared file; stray nested `.claude/settings.json` (dead config — root-only loading); a CLAUDE.md pointer whose target isn't loadable (wiki, Notion, code comment, non-markdown).
- **`move-to-<doc>`** — inline bloat in an instruction file (workflows, glossaries, API docs) that belongs in a linked doc with a one-line pointer left behind.
- **`add`** — a high-value catalog entry whose trigger matched but which is missing (harness: passes the annoyance filter; instructions: passes the earn-the-line filter).
- **`keep`** — earns its place: project-specific, changes behavior, non-duplicative.

## Harness checks

Against [CATALOG.md](CATALOG.md) "Harness" — the verified facts, catalog triggers, and anti-catalog:

- Re-declared global hooks → `cut` (additive scopes; fires twice) — **except** a guard hook under the CI/AFK carve-out ([ADR 0013](../../../docs/adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md)), which is correct to keep.
- Permissions: `deny`-only is the rule; any `allow` list → `fix-contradiction`.
- Missing triggered catalog hooks → `add`.

## Instruction-file checks

Against [CATALOG.md](CATALOG.md) "Instructions" — the earn-the-line filter, line classes, and anti-catalog:

- **Prefer enforcement over instruction.** Cut any line a hook (global or project) already enforces deterministically. Since the harness concern ran first, you know exactly what's enforced.
- **Progressive disclosure.** CLAUDE.md is an index, not a manual; long content moves out behind a pointer — and the pointer only earns its place if the target is clean, loadable, in-repo markdown.
- **Monorepo split** (if applicable): root holds only cross-cutting facts (repo layout, how to find the right app, shared tooling); per-app files hold only that app's specifics — they inherit global + root. Flag facts duplicated between root and an app file, or app-specific facts that leaked into root.

## Output

Per file/concern: the verb list with refs, then the proposed lean structure (trimmed tree + headers for instruction files; proposed key structure for the harness). Feeds the single batch approval in SKILL.md Step 5.
