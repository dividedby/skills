# setup-dividedby-skills and project-claude-config have non-overlapping scopes

Two skills in the `config/` bucket both operate on a target repo's configuration.
Without an explicit seam, a maintainer could invoke either for the wrong concern,
or a future edit could drag one into the other's territory.

## Context

`project-claude-config` grew from the merge of four earlier skills (ADR 0018) and
covers the Claude **harness** (`.claude/settings.json`, hooks, permissions) and the
Claude **instruction files** (`CLAUDE.md` / `AGENTS.md`). It is deliberately
scoped to what Claude's own config system enforces.

`setup-dividedby-skills` installs the broader `dividedby` operating conventions
into a target repo: the `docs/agents/` convention files (issue-tracker, labels,
domain, idea-inbox), the `## Conventions` block in the instruction file, the
GitHub label set, and the branching/merge policy. These are **not** Claude config
— they are the workflow agreements that govern how humans and agents collaborate
across all `dividedby` repos.

The two skills sometimes touch the same file (`CLAUDE.md`): `project-claude-config`
owns its structure and content; `setup-dividedby-skills` adds the `## Conventions`
block. This adjacency needs an explicit boundary to prevent double-handling.

## Decision

The seam is defined by **what owns the enforcement mechanism**:

- **`project-claude-config` owns the Claude harness and instruction files.** It
  decides what goes in `.claude/settings.json` (hooks, `env`, deny-only
  permissions) and what the instruction files say to Claude. When it touches
  `CLAUDE.md` / `AGENTS.md`, it owns the whole file — section structure,
  earn-the-line discipline, contradiction detection. Run this skill first on a
  greenfield repo.

- **`setup-dividedby-skills` owns the issue-tracker/labels/domain/idea-inbox
  conventions and the GitHub repository settings** (labels, branching/merge
  mechanics). When it writes to `CLAUDE.md` / `AGENTS.md`, it writes exactly
  one block: `## Conventions` and its pointer lines to `docs/agents/*.md`. It
  never restructures, audits, or trims the rest of the instruction file.

The `## Conventions` block in a target's `CLAUDE.md` is the one point of
adjacency. Ownership is by insertion origin:

- `project-claude-config` may note the block is absent and recommend adding it,
  but defers the actual insert to `setup-dividedby-skills`.
- `setup-dividedby-skills` inserts or updates the block without touching any
  other section.

## Consequences

- On a greenfield repo, the canonical order is: `project-claude-config` → then
  `setup-dividedby-skills`. Either may run independently on a repo that already
  has the other's work in place.
- `project-claude-config` does not scaffold `docs/agents/` files, reconcile
  GitHub labels, manage the Idea Inbox issue, or touch `~/.claude/branching-flow.md`.
- `setup-dividedby-skills` does not scaffold or audit `.claude/settings.json`,
  propose hooks, or enforce the earn-the-line bar on instruction content outside
  the `## Conventions` block.
- Future skills that touch repo configuration should self-locate against this axis
  (Claude harness/instructions vs. workflow conventions/GitHub settings) and not
  straddle it.
