# config/

Skills for configuring a project's Claude environment and managing its issue tracker.

## Skills

**[`project-claude-config`](./project-claude-config/SKILL.md)** — One state-routed pass for getting a project's Claude configuration right. It detects what exists and gives each concern the treatment it needs in a single pass — scaffolding what's missing, critiquing what's present, harness before instructions — so the user never self-diagnoses repo state or chains commands. What used to be four skills (init/audit × harness/instructions) survives as internal seams chosen from repo state ([ADR 0018](../../docs/adr/0018-config-is-one-state-routed-skill.md)).

The skill's contract — the earn-the-line bar, the Explore-gated interview, the propose-before-write posture — lives in the `SKILL.md`; its recommendations come from one fact-gated catalog covering both domains, [`project-claude-config/CATALOG.md`](./project-claude-config/CATALOG.md), validated against the catalog's canonical doc anchors before approval.

**[`triage`](./triage/SKILL.md)** — Moves issues through a state machine on our label vocabulary (`needs-triage` → `ready-for-agent` / `ready-for-human` / `blocked` / `wontfix`). Shows what needs attention, triages a specific issue with the appropriate outcome comment, and routes `skill-request` issues through the ADR-0021 prior-art scan rather than a generic path.

## Seam

`project-claude-config` owns the Claude **harness + instruction files** (`.claude/settings.json`, `CLAUDE.md`). `triage` owns the **issue-tracker workflow** (labels, state transitions, outcome comments). The skills are independent — run them in any order.
