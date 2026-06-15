# config/

Skills for getting a target repo's configuration and issue-tracker workflow
right. Three complementary skills with clean seams: one owns the Claude harness
and instruction files, one installs the `dividedby` workflow conventions and
GitHub settings, and one operates the issue-tracker workflow those conventions
define. The harness/conventions seam is defined in
[ADR 0023](../../docs/adr/0023-setup-dividedby-skills-vs-project-claude-config-seam.md).
On a greenfield repo, run `project-claude-config` and `setup-dividedby-skills`
first (in that order); reach for `triage` once the tracker is in use.

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

## [`triage`](./triage/SKILL.md)

The issue-tracker workflow skill. Moves issues through a state machine on our
label vocabulary (`needs-triage` → `ready-for-agent` / `ready-for-human` /
`blocked` / `wontfix`). Shows what needs attention, triages a specific issue with
the appropriate outcome comment, and routes `skill-request` issues through the
[ADR-0021](../../docs/adr/0021-skill-request-triage-runs-external-prior-art-scan.md)
prior-art scan rather than a generic path. It operates the label vocabulary that
`setup-dividedby-skills` installs.
