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
claude --version                             # built-in CLI skills ship with the binary
```

The built-in CLI skills are bundled in the Claude Code binary, not files under
`~/.claude/`, so they can't be `ls`-ed — read them off the session's available-skill
list and re-check after a `claude` upgrade.

## Globally installed skills

Matt Pocock's skill suite (`mattpocock/skills`, upstream of this repo's
`dividedby/skills`) and this repo's own published skills are installed globally
in `~/.claude/skills/`:

`apply-agent-research`, `autonomous-loop`, `caveman`, `context-firewall`,
`diagnose`, `find-skills`, `frontend-design`, `grill-me`,
`grill-with-docs`, `handoff`, `improve-codebase-architecture`,
`playwright-cli`, `project-claude-config`, `prototype`,
`setup-matt-pocock-skills`, `software-design`, `staleness-audit`, `tdd`,
`to-issues`, `to-prd`, `triage`, `write-a-skill`, `writing-beats`,
`writing-fragments`, `writing-shape`, `zoom-out`.

## Installed plugins

From `claude-plugins-official` (`anthropics/claude-plugins-official`):
`code-review`, `commit-commands`, `typescript-lsp`.

## Built-in CLI skills

Shipped with the Claude Code binary itself (not `~/.claude/` files), available in
every session: `claude-api`, `code-review`, `fewer-permission-prompts`, `init`,
`keybindings-help`, `loop`, `review`, `run`, `schedule`, `security-review`,
`simplify`, `update-config`, `verify`. These cover capabilities a remote run would
not otherwise see — notably `verify` (run-the-app verification of a change) and
`run` (launch/drive the app), the nearest neighbors to any release-QA or
verification skill-request.
