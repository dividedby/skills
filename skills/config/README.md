# config/

One state-routed skill for getting a project's Claude configuration right:
[`project-claude-config`](./project-claude-config/SKILL.md). It detects what
exists and gives each concern the treatment it needs in a single pass —
scaffolding what's missing, critiquing what's present — so the user never
self-diagnoses repo state or chains commands
([ADR 0018](../../docs/adr/0018-config-is-one-state-routed-skill.md)).

Manual/slash invocation only (`disable-model-invocation: true`). One bar:
**every line costs context or runs every session, so it must earn its
place.** Nothing here restates or weakens the global `~/.claude/` config; it
adds only project-specific value. Propose before writing; nothing is written
until approved.

## Two internal seams

What used to be four skills (init/audit × harness/instructions) survives as
internal seams the skill chooses from repo state:

- **Posture** (per concern): missing → **scaffold** (additive,
  [`scaffold-stubs.md`](./project-claude-config/scaffold-stubs.md)); present
  → **audit** (subtractive,
  [`audit-checklist.md`](./project-claude-config/audit-checklist.md)). A repo
  with a `settings.json` but no `CLAUDE.md` gets both in one run.
- **Ordering** (across concerns): the **harness** pass
  (`.claude/settings.json` — hooks, `env`, deny-only permissions) runs before
  the **instructions** pass (`CLAUDE.md` / `AGENTS.md`). A hook that enforces
  something automatically (deterministic, zero context cost) beats a
  CLAUDE.md line asking the agent to remember it — so settling the harness
  first lets the instructions pass *cut* anything a hook now enforces.

The interview is a **gap-filler gated behind Explore**: the skill asks only
what the repo can't reveal (intent, goals, invisible conventions), capped at
the stub bar — heaviest greenfield, near-silent on mature repos.

## Catalog

All recommendations come from one fact-gated catalog,
[`project-claude-config/CATALOG.md`](./project-claude-config/CATALOG.md),
covering both domains: hook/setting entries gated by the annoyance filter,
instruction-line entries gated by the earn-the-line filter — each with a
trigger, value, cost, and a canonical doc anchor. Proposals are validated
against live Claude Code docs (WebFetch on those anchors) before approval,
and settings writes route through the `update-config` skill.

Genuine judgment calls are surfaced for an optional `/grill-me` pass; domain
glossaries and ADRs belong to `/grill-with-docs`.
