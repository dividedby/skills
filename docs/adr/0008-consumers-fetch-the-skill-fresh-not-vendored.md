# Consumers fetch the skill fresh, they do not vendor it

A [Consumer](../../CONTEXT.md) with no plugin system (e.g.
`dividedby/agent-research`) obtains
[`apply-agent-research`](../../skills/meta/apply-agent-research/SKILL.md) by
**fetching it fresh from `dividedby/skills` each run** (clone-or-`npx
skills@latest add` into `~/.claude/skills/`), matching the existing
`improve-codebase-architecture.yml` pattern that clones `mattpocock/skills`
fresh each run. It does **not** commit a frozen vendored copy into its own tree.

Why: the leak guard and one-proposal gate are **code**, not prompt discipline. A
committed copy silently diverges from upstream — a stale leak guard could let
private content reach the public tracker, the worst failure this system has.
Fetching fresh keeps the guard current and removes any re-sync chore.

Trade-off: each scheduled run auto-executes whatever is at `dividedby/skills`
HEAD with the Consumer's tokens (`SKILLS_TRACKER_TOKEN`, the Claude token). We
accept this because the source is the *same maintainer's* repo, not a third
party, and Actions never passes secrets to fork-PR runs — the same trust
arch-review already extends to `mattpocock/skills`. A pinned-SHA variant
(deliberate, reviewed bumps) was rejected as over-engineering for a
single-maintainer, two-repo setup; revisit if Consumers ever span owners.

Because the fetched code is security-relevant, the Consumer runs the guard's
stdlib unit tests immediately after fetch and fails the run if they fail — so it
never files with a broken guard.

The skill is used **by file path** (the prompt reads `SKILL.md` and invokes
`lib/cli.py` by explicit path), not via Claude Code skill auto-discovery. So
`~/.claude/skills/` is parity convention, not a functional requirement — any
readable location (e.g. a cloned temp dir) works equally, and a `claude-code-base-action`
consumer needs no discovery/config step. Confirmed in agent-research's first
fetch-fresh run.
