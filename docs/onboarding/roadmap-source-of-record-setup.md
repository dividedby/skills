# Stand up the roadmap-as-source-of-record pattern

This stands up a **human-readable roadmap as the execution source of record**:
one Markdown doc with a master census (one row per issue) that is the single
place you go to pick the next thing to work on, kept honest by two cheap hooks
and reconciled by the [`doc-regen`](../../skills/engineering/doc-regen/SKILL.md)
skill.

The three parts compose into a closed loop:

1. **`roadmap.md`** — the census; the only doc you read to choose work.
2. **A PreToolUse `git commit` guard** (`roadmap-guard.py`) — in-branch
   enforcement: an issue-referencing commit must touch the roadmap.
3. **A SessionStart drift nudge** (`roadmap-drift-nudge.py`) — catches
   *out-of-band* drift (issues opened/closed via `gh`/web *between* sessions,
   which the commit guard structurally can't see), and points at `/doc-regen`.

`doc-regen` is the reconcile half: the guard keeps the doc fresh *inside* a PR;
the nudge tells you when *between-PR* drift has accumulated; the skill fixes it.

## The turn-key path

In a repo with issues but no roadmap, run **`/doc-regen`**. It detects the empty
state and **bootstraps the whole pattern** — drops the roadmap template, backfills
one census row per open issue, writes both hooks into `.claude/hooks/`, wires
`settings.json`, and runs a first reconcile pass to populate statuses/waves/deps.
It writes everything to the working tree for review and **commits nothing**: you
review `git diff` + the new untracked files and commit.

If a legacy planning doc already exists (an older `ROADMAP.md`, a TODO/tracking
doc), `/doc-regen` instead **migrates** it — proposing a mapping into the canonical
census before reshaping, preserving your prose.

## What bootstrap creates, and why

Everything repo-specific is three things, hoisted to a config block at the top of
each hook so adoption is "edit a few constants":

- **`ROADMAP` path** — where the doc lives (`docs/plans/roadmap.md` default,
  `ROADMAP.md`, …). The hooks and the skill share this constant.
- **Census column indices** — `ISSUE_COL` / `STATUS_COL` (zero-based) tell the
  nudge's parser which pipe-delimited columns hold the issue number and the
  status. The template ships the default schema
  `| # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |`; the parser
  keys off index, so a repo with a differently-shaped table just sets the indices.
- **Status vocab** — `DONE_TOKEN`, the substring (lowercased) in a status cell
  that means closed/done.

The artifacts are pure Python stdlib
([ADR 0004](../adr/0004-runbook-helpers-are-python-stdlib.md)) and live as
**templates** under the skill
([`templates/`](../../skills/engineering/doc-regen/templates/)) — they are not
active hooks in this repo; bootstrap copies them into a consumer.

### `settings.json` wiring

```jsonc
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [
        { "type": "command", "command": ".claude/hooks/roadmap-guard.py",
          "if": "Bash(git commit*)", "timeout": 15,
          "statusMessage": "Checking roadmap is updated..." }
      ]}
    ],
    "SessionStart": [
      { "hooks": [
        { "type": "command", "command": ".claude/hooks/roadmap-drift-nudge.py",
          "timeout": 15, "statusMessage": "Checking roadmap for out-of-band drift..." }
      ]}
    ]
  }
}
```

A project-scope hook may redeclare a global guard for CI/AFK parity
([ADR 0013](../adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md)).

## Manual setup (if you'd rather not let the skill scaffold)

1. Copy [`templates/roadmap.md`](../../skills/engineering/doc-regen/templates/roadmap.md)
   to your chosen path; backfill one row per open issue.
2. Copy the two hooks under `.claude/hooks/`, edit the config block (path / column
   indices / status vocab), `chmod +x`.
3. Wire `settings.json` (snippet above).
4. `npx skills@latest add dividedby/skills` → pick `doc-regen`.
5. **Smoke-test:** run the parser test
   (`python3 .claude/hooks/roadmap-drift-nudge.test.py`) to confirm your column
   config; run the nudge by hand (`echo '{}' | .claude/hooks/roadmap-drift-nudge.py`)
   and confirm it reports your real drift; run `/doc-regen` once to reconcile.

## Posture

`doc-regen` edits the working tree for review and writes **additive** issue
comments (unblock/routing/sequencing notes); it **never commits, never closes an
issue, never rewrites a body** — see
[ADR 0017](../adr/0017-doc-regen-write-posture.md). If you ever wire it into an
unattended loop, suppress the issue-write surface (propose-only), the same way the
staleness-review loop suppresses its apply station.
