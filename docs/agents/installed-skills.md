# Installed Skills

A snapshot of the **external skills and plugins available in the maintainer's
global environment** — capabilities present in every Claude Code session in this
repo, whether or not they ship as files under this repo's own `skills/`.

## Why this file exists

Skills that ask *"does this capability already exist?"* — chiefly
[`apply-agent-research`](../../skills/meta/apply-agent-research/SKILL.md) — read
the host repo's own governance docs as their already-do-this baseline. That
baseline is blind to skills installed **outside** the repo (in `~/.claude/`), so
the loop can propose rebuilding a capability the maintainer already has. Issue
#43 ("add a grill-with-docs skill") was exactly this miss: the skill is installed
globally, just not as a file here.

The loop runs **remotely in CI**, so it cannot enumerate the maintainer's local
install at run time. This committed snapshot is the only installed-skill signal a
remote run can read. Treat it as **already-present capability**: do not propose
rebuilding any of it — propose *integrations* or *novel uses* with this repo's
own skills instead.

## Refreshing this file

Maintainer-maintained; update it when the global install set changes:

```
ls ~/.claude/skills/                         # globally installed skills
python3 -m json.tool ~/.claude/plugins/installed_plugins.json   # installed plugins
```

## Globally installed skills

Matt Pocock's skill suite (`mattpocock/skills`, upstream of this repo's
`dividedby/skills`) and this repo's own published skills are installed globally
in `~/.claude/skills/`:

`apply-agent-research`, `audit-project-claude`, `audit-project-harness`,
`caveman`, `diagnose`, `find-skills`, `frontend-design`, `grill-me`,
`grill-with-docs`, `handoff`, `improve-codebase-architecture`,
`init-project-claude`, `init-project-harness`, `playwright-cli`, `prototype`,
`setup-matt-pocock-skills`, `software-design`, `tdd`, `to-issues`, `to-prd`,
`triage`, `write-a-skill`, `zoom-out`.

## Installed plugins

From `claude-plugins-official` (`anthropics/claude-plugins-official`):
`code-review`, `commit-commands`, `typescript-lsp`.
