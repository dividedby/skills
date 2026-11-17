# Idea capture moves to the idea-intake skill

> **Status: Accepted** — maintainer decision (2026-11-17).

## Context

Each project repo carried a roughly 12-line "Intake convention" block in its
`CLAUDE.md`: on "file an idea" or an unqualified "file an issue", append an enriched
row to the repo's Idea Inbox issue; on "file a tracked issue" or a plainly-scoped bug,
file a `needs-triage` issue. About a dozen repos held near-identical copies, each
with its own drift, and `docs/agents/idea-inbox.md` said the Inbox "stays a
convention, not a skill or a hook".

## Decision

Capture moves to the `idea-intake` skill, which fires on those phrases in any repo.
It resolves `owner/repo` from the git remote, finds the Inbox by its `idea-inbox`
label over `gh api` REST, and prepends the row. Each repo's `CLAUDE.md` keeps one
line pointing at its Inbox issue.

A repo's `docs/agents/idea-inbox.md` stays the protocol for capture and drain, and
where it differs from the skill it wins; the skill reads it first. Drain stays a
convention: a doc plus the issue body's breadcrumb, with no skill or hook.

## Consequences

- One copy of the capture rules to maintain, not one per repo.
- The skill omits `disable-model-invocation` so it can fire on the phrase, which
  puts its description in every session's context. This is a deliberate exception to
  the user-invoked default.
- Per-repo behavior changes go in `docs/agents/idea-inbox.md`, not in the skill.
- Zero or several open Inbox issues make the skill ask rather than guess.
