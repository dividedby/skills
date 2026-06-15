# config/

Two complementary skills for getting a target repo's configuration right. The
seam between them is defined in
[ADR 0023](../../docs/adr/0023-setup-dividedby-skills-vs-project-claude-config-seam.md):
one owns the Claude harness and instruction files; the other owns the workflow
conventions and GitHub settings. On a greenfield repo, run them in this order.

## [`project-claude-config`](./project-claude-config/SKILL.md)

The Claude config skill. Detects what exists and gives each concern the treatment
it needs in a single pass — scaffolding what's missing, critiquing what's present,
harness before instructions — so the user never self-diagnoses repo state or chains
commands. What used to be four skills (init/audit × harness/instructions)
survives as internal seams chosen from repo state
([ADR 0018](../../docs/adr/0018-config-is-one-state-routed-skill.md)).

The skill's contract — the earn-the-line bar, the Explore-gated interview,
the propose-before-write posture — lives in the `SKILL.md`; its
recommendations come from one fact-gated catalog covering both domains,
[`project-claude-config/CATALOG.md`](./project-claude-config/CATALOG.md),
validated against the catalog's canonical doc anchors before approval.

## [`setup-dividedby-skills`](./setup-dividedby-skills/SKILL.md)

The conventions skill. Installs the `dividedby` operating conventions into a
target repo: `docs/agents/` convention files, the `## Conventions` block in the
instruction file, the GitHub label set (reconciled against
[`docs/agents/labels.md`](../../docs/agents/labels.md)), and the branching/merge
policy (from `~/.claude/branching-flow.md`). Every network mutation is behind a
mandatory report-then-confirm gate.
