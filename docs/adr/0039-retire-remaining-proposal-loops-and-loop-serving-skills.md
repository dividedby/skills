# Retire the remaining proposal loops and the skills that served them

> **Status: Accepted** — maintainer decision (2026-10-12), taken after [ADR 0038](./0038-retire-knowledge-application-after-agent-research-decommission.md) retired the knowledge-application loops and left three loops, the harness and a fleet-drift check running.

## Context

[ADR 0038](./0038-retire-knowledge-application-after-agent-research-decommission.md)
retired everything fed by the archived `dividedby/agent-research` KB and left the
rest of the proposal-loop family running: `improve-codebase-architecture`,
`staleness-review` and `changelog-health`, the fleet-drift family
(`fleet-drift.yml`, which ran the four detectors under `tools/`), and the skills
that stood those loops up in other repos.

On 2026-10-12 the maintainer decided to retire all of it: with the KB-fed half
gone, the remaining loops, harness and loop-serving skills no longer justify
their upkeep.

## Decision

**Retire every remaining scheduled proposal loop, the fleet-drift family, and the
three skills that existed to serve them.**

- Delete the `improve-codebase-architecture`, `staleness-review` and
  `changelog-health` workflows, the two reusable bodies, and
  `.github/arch-review-context.md`.
- Delete `fleet-drift.yml` and the four drift detectors under `tools/`
  (workflow-drift, label-drift, idea-inbox-drift, loop-liveness) with their shared
  helper.
- Delete `harness/` entirely: `cli.py`, its prompts, the changelog-health
  evaluator and their tests. The `claude-loops-v1` tag has no remaining consumer
  and is deleted by hand after merge.
- Delete the skills `staleness-audit`, `setup-dividedby-skills` and
  `workflow-onboarding`, and remove them from the plugin manifest and README.
- Delete the `check-installed-skills` Stop hook and `docs/agents/installed-skills.md`
  it guarded, and the loop-authoring docs (`workflow-authoring.md`,
  `vendored-workflows.md`, `harness-baseline.md`, `docs/onboarding/`), plus the
  `skills/config/README.md` bucket index.
- Reduce the label convention to the **CORE** tier (plus repo-private **LOCAL**
  labels). The LOOP/NETWORK and CHANNELS tiers, including
  `awaiting-corroboration`, leave the convention, and `skills/config/labels.test.py`
  keeps only its CORE assertions.
- Rework `CONTEXT.md`: drop the Consumer, Proposal-loop harness, Repo-context
  include, Lens, Legibility and Workflow envelope terms. **Proposal loop** stays as
  the propose-only point on the `autonomous-loop` gate spectrum.
- Drop "LLM-evaluated" from the fleet changelog rule. Changelogs stay
  hand-maintained ([ADR 0034](./0034-fleet-changelogs-are-hand-maintained-and-llm-evaluated.md)),
  and the grading checklist remains as a manual self-check.
- Leave disabled or archived consumer repos alone; this ADR does not edit any other
  repository.

**Unaffected:** the **Idea Inbox** intake convention and its `idea-inbox` label,
the `check-skill-registration` Stop hook, the `git-guard` hook (kept; only its
comments change), the remaining ten skills, and the soft-dependency posture
toward `mattpocock/skills` and `anthropics/claude-plugins-official`
([ADR 0024](./0024-lean-on-upstream-skills-soft-depend-over-reinvent.md)).

ADRs whose subject is wholly retired are marked superseded by this ADR; those whose
decision partly survives carry a "superseded in part" note. A few ADRs (e.g.
[0036](./0036-council-skill-drives-workflow-tool.md)) get an "in part" note only
because they link files this change deletes. Their bodies are not
rewritten.

## Consequences

- The published catalog shrinks by three skills (flagged **Breaking** in the
  changelog), and the repo no longer ships `harness/`; the changelog rolls to 2.0.0.
- Any consumer repo still calling a deleted reusable workflow, or using a deleted
  skill, must remove that reference. Cleaning those up, deleting the loop-related
  labels and open loop-filed issues, and revoking `ISSUES_TOKEN` are manual
  post-merge steps outside this change.
- `project-claude-config` still detects label-doc drift (its Lens 4), but the fix is
  now a by-hand reconciliation against `docs/agents/labels.md` rather than a
  hand-off to a setup skill.
- Rejection records under `.out-of-scope/`, design docs under `docs/design/`, and
  older changelog entries that name the retired pieces are left as history.
- Reinstating a scheduled loop would need a new decision and a new ADR; none of the
  deleted machinery is kept beyond git history.
