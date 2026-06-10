# The Idea Inbox intakes unstructured ideas only; every filing registers in the Roadmap

The maintainer wanted a single intake — "any time I say file an issue or file an
idea, it goes to the Idea Inbox" — and to reroute *all* issue-filing workflows
through it. But the repo's structured filing flows are deliberately direct:
`apply-agent-research` files capped, capability-keyed skill-requests with `+1`
cross-repo corroboration and a leak guard (ADRs 0006/0009/0011/0019), and its
promotion (drain) step is interactive (`/grill-with-docs`, `/to-prd`). A cron
proposal cannot be grilled at file time, and a freeform inbox would destroy the
dedup/`+1` machinery that is the whole point of those flows.

## Decision

The **Idea Inbox is the canonical intake for *unstructured*, human-originated
ideas only.** Items enter **enriched** (the idea plus the ambient context/links
available at file time, not yet grilled or scoped) and leave by **draining** — an
adaptive promotion, **self-prescribed in the Inbox issue body** (no skill), that
picks only the pipeline steps each idea needs and strives to emit a
`ready-for-agent` issue (strong agent brief per #196, HITL steps where needed).

**Structured, contract-bearing filings** (skill-request, skill-promotion, a
fully-scoped bug) **bypass the Inbox** and file labeled issues directly.

The unifying invariant: **every filing registers in the Roadmap — not every
filing funnels through the Inbox.** Enforcement already exists: the SessionStart
drift nudge flags any open issue missing from the census, so both drained and
directly-filed issues get slotted by reconcile with no new mechanism.

Intake is a CLAUDE.md convention, not a skill. The Inbox list is **flat** (`##
Ideas` newest-on-top + `## ✅ Actioned`): type emerges at drain, priority lives
in the roadmap's waves.

## Rejected alternatives

- **Universal funnel — every filing path deposits into the Inbox first.** Breaks
  the structured proposal loops (capability keys, `+1`, caps) and cannot host
  their cron, non-interactive filing. Rejected.
- **Sectioning the Inbox by type or priority.** Forces a file-time classification
  that doesn't exist for a raw idea and duplicates the roadmap's wave ordering.
  Rejected in favor of a flat list.
- **A dedicated `drain-inbox` skill.** Drain is self-prescribed in the Inbox body
  (same pattern as the roadmap doc's self-executing "how to use" section), so a
  skill is unneeded ceremony.
