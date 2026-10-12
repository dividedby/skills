# Retire knowledge application after the agent-research decommission

> **Status: Accepted** — maintainer decision (2026-10-11), taken when `dividedby/agent-research` was archived (its ADR 0032) and the `agent-research-knowledge` mirror repository was deleted.

## Context

`dividedby/agent-research` was the private knowledge base (KB) that fed this repo's
"knowledge application" machinery. It was archived on 2026-10-11, and its public
read-only mirror, `dividedby/agent-research-knowledge`, no longer exists (the repo
returns 404). Every input that machinery depended on is gone:

- **`apply-agent-research`** — the skill (`skills/meta/apply-agent-research/`), its
  scheduled loop and reusable workflow, and its harness prompt — read the mirror
  plus the host repo's governance docs and proposed one agent-meta improvement per
  run ([ADR 0003](./0003-skill-improvement-workflows-propose-via-issues.md),
  [ADR 0029](./0029-apply-agent-research-joins-the-reusable-body-rail.md)).
- The **`skill-request` / `skill-promotion` flows** were filed only by that loop
  ([ADR 0006](./0006-skill-request-demand-corroboration.md),
  [ADR 0009](./0009-skill-request-checks-existing-and-installed-skills.md),
  [ADR 0010](./0010-consumers-audit-local-skills-supply-side.md),
  [ADR 0021](./0021-skill-request-triage-runs-external-prior-art-scan.md)).
- **`skill-divergence-audit`** ([ADR 0037](./0037-wire-skill-divergence-audit-as-a-recurring-loop.md))
  compared this repo's skills against `mattpocock/skills` *and* the agent-research
  KB, and reused the apply skill's `sanitizer` and `proposal_gate`.
- **`tools/export_scaffolding.py`** bundled the loops' agent-meta surfaces for
  external deep research; its manifest covered the apply and architecture loops.

No consumer repo calls `apply-agent-research` any more (goodreads-bot #855,
moodreader #978, and claude-config #190 removed their callers). The cross-repo cost
ledger (`COST_SURFACE` in `agent-research`) is discontinued, and the global rule
requiring headless-Claude CI jobs to onboard into it was removed
(claude-config #189).

Three other loops are **live and independent** of the KB: `improve-codebase-architecture`
and `staleness-review` (run by goodreads-bot and moodreader; `staleness-review` also
by dokdiv) and `changelog-health`. They clone this repo's `main` and use
`harness/cli.py` and their own prompts under `harness/prompts/`.

## Decision

**Retire knowledge application entirely, plus the two satellites that depended on
it.**

- Delete the `apply-agent-research` skill, its workflow and reusable workflow, its
  harness prompt, and the `repair_json` drift guard whose other half it was
  ([ADR 0026](./0026-repair-json-duplicated-under-drift-guard.md)); `harness/cli.py`
  keeps its own `_repair_json` and tests.
- Retire the `skill-request` and `skill-promotion` flows, their design docs, the
  Consumer onboarding doc, and the triage path for `skill-request` issues.
- Retire `skill-divergence-audit` (skill, loop, prompt). Skills-vs-upstream
  comparison becomes a manual, on-demand check. The `skills/meta/` bucket ceases to
  exist.
- Retire `tools/export_scaffolding.py` and its manifest.
- Retire the labels `source:agent-research`, `source:skill-audit`, `skill-request`,
  and `skill-promotion` from the convention; `awaiting-corroboration` is left as the
  sole CHANNELS-tier row so the CORE / LOOP-NETWORK / CHANNELS structure the
  label-drift detector fingerprints stays intact.
- Drop `dividedby/agent-research` from the fleet drift, label-drift, idea-inbox-drift,
  and loop-liveness rosters.
- Drop the requirement that new `claude -p` workflows onboard into the cross-repo
  `COST_SURFACE` ledger. The exact-model pin, `--max-budget-usd` backstop, `digest`
  cost line, and hash-stagger rules remain.
- Leave disabled loops disabled; this ADR does not change any workflow enable state.

**Unaffected:** `improve-codebase-architecture`, `staleness-review`, and
`changelog-health` (workflows, reusable bodies, harness prompts, `harness/cli.py`
behaviour); the `claude-loops-v1` tag and the reusable-body rail
([ADR 0014](./0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md));
`fleet-drift.yml`.

ADRs whose subject is wholly retired are marked superseded by this ADR; those whose
subject partly survives carry a "superseded in part" note. Their bodies are not
rewritten.

## Consequences

- The repo's published catalog shrinks by two skills and one bucket; consumers of
  the plugin that referenced them must drop those references (flagged **Breaking**
  in the changelog).
- The GitHub labels listed above remain on the tracker until deleted by hand; only
  their documentation and tests are removed here.
- The proposal-loop family is now two vendored loops plus the host-only
  `changelog-health`. The harness rail, thin-stub model, and fetched-fresh
  harness are unchanged.
- Docs that described the KB / mirror / Consumer-network vocabulary are reworded or
  deleted. Rejection records under `.out-of-scope/` and unreleased changelog lines
  that mention the retired pieces are left as history.
- Reinstating a KB-fed loop would need a new decision and a new ADR; none of the
  deleted machinery is kept for it beyond git history.
