# CLAUDE.md compaction-steering rule — not added to this repo

**Rejected as:** a standing `## Compact Instructions` section in this repo's `CLAUDE.md`.

**Why:** a repo-scoped `## Compact Instructions` rule reliably steers only the **main session's** auto-compaction (the documented mechanism — `code.claude.com/docs/en/how-claude-code-works.md`, "When context fills up"). In *this* repo the main session is either a short interactive session or a bounded AFK proposal loop (scout → rank → file ≤2 issues); neither reaches the auto-compaction threshold, so the rule would be permanent context cost for an event that never fires. The rare long *interactive* session is already covered at zero standing cost by the per-invocation `/compact focus on <X>`.

The one place a standing rule could earn its keep — long, **unattended** subagent runs that auto-compact with no human to type `/compact` — rests on three behaviours that are all **undocumented** (claude-code-guide, 2026-06-24): whether subagents inherit `CLAUDE.md`, whether subagents auto-compact at all, and whether a `## Compact Instructions` section steers a subagent's compaction. Cannot be relied on. And even if those held, the benefit would be fleet-wide, not skills-specific → it belongs in global `~/.claude/CLAUDE.md` (`claude-config`), not here.

The originating proposal came from a generic "manage the session context actively" best-practice mirrored by the apply-agent-research loop; it was not checked against whether this repo actually has the problem. It does not.

**Bar to revisit:** a long-running **unattended** agent in this repo that demonstrably auto-compacts (fills its window across enough turns), **and** empirical confirmation that a `## Compact Instructions` rule steers that compaction. Until both hold, the on-demand `/compact focus` is the right tool.

## Prior requests
- `dividedby/skills#442`
