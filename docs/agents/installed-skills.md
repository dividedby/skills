# Installed Skills

A snapshot of the **external skills and plugins available in the maintainer's
global environment** — capabilities present in every Claude Code session in this
repo, whether or not they ship as files under this repo's own `skills/`.

## Why this file exists

Anything that asks *"does this capability already exist?"* and reads only the
repo's own governance docs is blind to skills installed **outside** the repo (in
`~/.claude/`), so it can propose rebuilding a capability the maintainer already
has. Issue #43 ("add a grill-with-docs skill") was exactly this miss: the skill
is installed globally, just not as a file here.

A remote CI run cannot enumerate the maintainer's local install, so this
committed snapshot is the only installed-skill signal it can read. Treat it as
**already-present capability**: do not propose rebuilding any of it — propose
*integrations* or *novel uses* with this repo's own skills instead.

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

A subset of Matt Pocock's skill suite (`mattpocock/skills`, upstream of this
repo's `dividedby/skills`), this repo's own published skills, and one local skill
are installed globally in `~/.claude/skills/`:

`autonomous-loop`, `cba-searching`, `code-review`, `council`, `doc-it`,
`flow-pr`, `frontend-design`, `grill-with-docs`, `handoff`,
`improve-codebase-architecture`, `project-claude-config`, `repo-audit`,
`setup-dividedby-skills`, `software-design`, `staleness-audit`, `tdd`,
`to-spec`, `to-tickets`, `triage`, `workflow-onboarding`, `write-well`.

Of these, Matt's are `code-review`, `grill-with-docs`, `handoff`,
`improve-codebase-architecture`, `tdd`, `to-spec`, and `to-tickets`;
`cba-searching` is a local skill; the rest are this repo's own skills.
`setup-dividedby-skills` and `triage` (config bucket, issues #292 / #293) are
installed globally; the dividedby `triage` is the version that resolves for the
`triage` name in this repo's workflow.

The set was trimmed on 2026-10-12 (see the
[ADR 0024](../adr/0024-lean-on-upstream-skills-soft-depend-over-reinvent.md)
amendment); anything not listed here is not installed.

## Installed plugins

`terrashark` — Terraform/OpenTofu structure, security, and testing guardrails;
installed project-scoped to `~/repos/infra` only, not available in this
repo's own sessions.

From `claude-plugins-official` (`anthropics/claude-plugins-official`):
`typescript-lsp`, `pyright-lsp`.

## Built-in CLI skills

Shipped with the Claude Code binary itself (not `~/.claude/` files), available in
every session: `claude-api`, `code-review`, `fewer-permission-prompts`, `init`,
`keybindings-help`, `loop`, `review`, `run`, `schedule`, `security-review`,
`simplify`, `update-config`, `verify`. (`code-review` also exists as an
installed `~/.claude/skills/` entry above — the binary-shipped version is a
distinct skill of the same name.) These cover capabilities a remote run would
not otherwise see — notably `verify` (run-the-app verification of a change) and
`run` (launch/drive the app), the nearest neighbors to any release-QA or
verification skill.
