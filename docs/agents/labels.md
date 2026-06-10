# Label Convention

The canonical source of truth for issue-label **names, colors, and descriptions**
across all of `dividedby`'s repos. The triage-role mapping in
[`triage-labels.md`](./triage-labels.md) names the five triage roles; this file is
the fuller reference — every label, its hex color, and its one-line description.

Labels fall into three tiers plus a remove-stock rule.

## Tiering rule

- **CORE** — every repo carries these.
- **LOOP/NETWORK** — only repos that run the proposal loops (full-tier repos). Seed
  the `source:*` label for a loop only when the repo actually runs it; the workflow
  auto-creates it on first use, so pre-seeding with the canonical color just makes
  that auto-create a no-op.
- **CHANNELS** — owned by `dividedby/skills`; consumer repos *apply* them but never
  create them (a fine-grained `Issues:write` token may not cover label creation).

Domain one-off labels stay **local** and untouched (e.g. `anti-bot-resilience`,
`blocked-on-skrabe`, agent-research's corpus labels). The convention governs the
shared vocabulary, not a repo's private labels.

## CORE (all repos)

| Label             | Color    | Description                                                       |
| ----------------- | -------- | ---------------------------------------------------------------- |
| `needs-triage`    | `FBCA04` | Maintainer needs to evaluate this issue                          |
| `needs-info`      | `D93F0B` | Waiting on reporter for more information                         |
| `ready-for-agent` | `0E8A16` | Fully specified, ready for an AFK agent                          |
| `ready-for-human` | `1D76DB` | Requires human implementation                                    |
| `wontfix`         | `FFFFFF` | Will not be actioned                                             |
| `idea-inbox`      | `D4C5F9` | The single freeform idea-intake issue for this repo (one per repo) |

## LOOP/NETWORK (full-tier repos)

| Label                          | Color    | Description                                                       |
| ------------------------------ | -------- | ---------------------------------------------------------------- |
| `workflow-onboarding`          | `0052CC` | Onboarding this repo to a proposal-loop workflow                 |
| `source:agent-research`        | `5319E7` | Filed by the apply-agent-research loop                           |
| `source:architecture-review`   | `5319E7` | Filed by the improve-codebase-architecture loop                  |
| `source:staleness-review`      | `5319E7` | Filed by the staleness-review loop                               |
| `source:skill-audit`           | `5319E7` | Supply-side redundant-local-skill finding                        |
| `awaiting-corroboration`       | `BFD4F2` | Triaged but parked pending cross-repo corroboration (ADR 0006)   |

## CHANNELS (owned by `dividedby/skills`, applied by consumers)

| Label             | Color    | Description                                                |
| ----------------- | -------- | --------------------------------------------------------- |
| `skill-request`   | `006B75` | Cross-repo demand for a skill (aggregated per ADR 0006)   |
| `skill-promotion` | `D93FB3` | Cross-repo offer of a local skill for promotion           |

These were recolored off `0E8A16`/`1D76DB`, which collided with
`ready-for-agent`/`ready-for-human`. Changing channel colors must be coordinated so
consumer repos recolor in step — the per-repo "Adopt label convention v1" issues
handle the consumer side.

## Remove stock

Every repo removes these unused GitHub stock defaults:

`bug`, `documentation`, `duplicate`, `enhancement`, `good first issue`,
`help wanted`, `invalid`, `question`.

Before deleting a stock label, re-label any issue carrying it onto the appropriate
convention label (most carry zero issues, or already carry a convention label).
