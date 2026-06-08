# <project> — Execution Roadmap (source of record)

> **Status:** active · **Owner:** maintainer + agents
>
> The authoritative execution roadmap. Every open issue appears in the master
> census below, and this is the single place to go to pick the next thing to
> work on. **This document self-updates:** every PR that opens, advances, or
> closes an issue updates that issue's row in the same branch — a PreToolUse hook
> (`.claude/hooks/roadmap-guard.py`) enforces it. Out-of-band drift (issues
> changed via `gh`/web between sessions) is caught by a SessionStart nudge
> (`.claude/hooks/roadmap-drift-nudge.py`) and repaired with `/doc-regen`.

## How to use this doc (read this as your instructions)

You have been pointed here to work the backlog. This section *is* the prompt —
no other guidance is needed. Follow it top to bottom:

1. **Pick the work.** From the top priority wave, take the earliest row whose
   `Status` is `Next` and whose `Deps` are all satisfied (closed). If the top
   wave has no unblocked `Next`, drop to the next wave. Ties break by row order.
2. **Read the issue in full — body *and* every comment.** Open the linked issue
   (`gh issue view <#> --comments`). The **issue body is authoritative** for
   scope and acceptance criteria; the **comments carry live guidance** —
   unblock notes, routing, and sequencing that `/doc-regen` writes back as the
   roadmap reconciles. Do not act on the body alone; a comment may have changed
   the plan. This census row only *routes and orders* — it never restates scope.
3. **Invoke the routed skill.** Use the skill(s) named in the row's `Skill(s)`
   cell as your method; honor the `Notes` cell for any roadmap-only sequencing.
4. **Update this doc's row in your branch before you commit** (the guard hook
   blocks an issue-referencing commit otherwise): set `Status`, and update
   `Deps` on anything your change unblocks.

## Priority waves
| Wave | Theme | Issues | Gate to enter |
| ---- | ----- | ------ | ------------- |
| **W1** | <theme> | #NN #NN | none — active now |
| **—**  | Cross-cutting / ongoing | #NN | n/a |

## Master census (all open issues)
| # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |
| - | ----- | ---- | ------ | ----- | -------- | ---- | ----- |
| NN | <short title> | W1 | **Next** | agent | `/tdd` | — | — |

## Legend
- **Status** — `Next` (do now) · `Backlog` (ready, unstarted) · `Blocked`
  (waiting on a dep) · `Parked` (deferred/needs-design/wontfix) · `Tracking`
  (epic/PRD parent) · `Done` (closed).
- **Owner** — `agent` · `human` · `mixed`.
- **Deps** — blocking issues; _italic_ = already closed (satisfied).
- **Notes** — roadmap-only sequencing guidance. Scope/AC live in the issue, not here.

## Self-update protocol
Any PR that opens/advances/closes an issue updates that issue's census row
(minimally `Status`, plus `Deps` on anything it unblocks). Closed → `Status: Done`
(keep the row). Enforced by `roadmap-guard.py`; out-of-band drift repaired by `/doc-regen`.
