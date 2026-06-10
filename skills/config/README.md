# config/

One state-routed skill for getting a project's Claude configuration right:
[`project-claude-config`](./project-claude-config/SKILL.md). It detects what
exists and gives each concern the treatment it needs in a single pass —
scaffolding what's missing, critiquing what's present, harness before
instructions — so the user never self-diagnoses repo state or chains
commands. What used to be four skills (init/audit × harness/instructions)
survives as internal seams chosen from repo state
([ADR 0018](../../docs/adr/0018-config-is-one-state-routed-skill.md)).

The skill's contract — the earn-the-line bar, the Explore-gated interview,
the propose-before-write posture — lives in the `SKILL.md`; its
recommendations come from one fact-gated catalog covering both domains,
[`project-claude-config/CATALOG.md`](./project-claude-config/CATALOG.md),
validated against the catalog's canonical doc anchors before approval.
