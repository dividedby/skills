# skill-request triage runs an external prior-art scan

Skill-request triage runs a GitHub-wide prior-art scan via the installed
`cba-searching` skill before the maintainer accepts, parks, or rejects a request.
This is the **external** counterpart to
[ADR 0009](0009-skill-request-checks-existing-and-installed-skills.md): ADR 0009
checks the candidate capability against skills that already exist *inside* this
ecosystem (the published catalog plus the installed-skill snapshot) at Consumer
**filing** time; this scan asks whether the wider open-source world already ships
the capability well, at maintainer **triage** time. `cba-searching` is referenced
as an installed skill ([`docs/agents/installed-skills.md`](../agents/installed-skills.md)),
not vendored here.

## Context

ADR 0009 stops a Consumer from re-requesting a capability that this ecosystem
already provides. It does not ask the orthogonal question: *does a good
off-the-shelf tool already exist outside this ecosystem?* A request can clear the
ADR-0009 internal filter — genuinely net-new to `dividedby/skills` and the
installed set — and still be redundant with a mature public project that the
maintainer should adopt or reference instead of writing a new skill. Catching
that is the maintainer's call at triage, not the Consumer's at filing.

## Decision

The external prior-art scan sits at **triage time as a human aid**, not as an
in-loop filing-time gate. `cba-searching` is a manual, interactive,
blunt-verdict skill: it fits a human deciding accept/park/reject, and its output
(a landscape verdict) is exactly the input a triage decision wants. The flow is
documented in
[`skill-request-flow.md`](../design/skill-request-flow.md) at the triage stage.

The scan complements ADR 0009; it does not replace or modify it. The Consumer-side
internal check stays where it is (pre-filing, in the loop). Two checks, two
surfaces, two actors: ADR 0009 is automatic and internal at filing; this is
human and external at triage.

## Rejected alternative: an in-loop filing-time gate

Running a GitHub-wide scan inside every headless `apply-agent-research` Consumer
run was considered and rejected:

- **Cost and non-determinism.** A GitHub-wide search on every run adds latency,
  API cost, and a non-deterministic external dependency to a loop that is
  otherwise self-contained — the same standing-cost-surface concern that closed
  #257.
- **Wrong fit for the skill.** `cba-searching` is interactive and produces a
  blunt human-facing verdict; it is not built to run unattended in a headless
  Consumer loop and emit a machine gate.
- **Right actor already exists.** The maintainer already triages every
  `skill-request` (accept/park/reject); the scan is one more input to a decision
  they are already making, so it needs no new automation.

## Consequences

- The triage stage of `skill-request-flow.md` names the scan step and when it
  runs; it does not re-derive `cba-searching`'s internal procedure
  ([ADR 0002](0002-design-skills-prescribe-at-principle-level.md)).
- No new skill, hook, CI, or automation is introduced. `cba-searching` is
  referenced as an installed skill ([ADR 0007](0007-already-do-this-baseline-includes-installed-skills.md),
  `docs/agents/installed-skills.md`), never vendored into `skills/`.
