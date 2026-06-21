# Staleness-review findings already inside Dependabot's ecosystem scope

**Rejected:** Triaging staleness-review findings into agent work when the flagged
dependency is already covered by an active Dependabot ecosystem.

**Why:** Dependabot owns library and action version bumps for every ecosystem
configured in `.github/dependabot.yml` (currently `github-actions`, weekly). When
the staleness-review loop reports a bump that falls inside that scope — e.g.
`actions/checkout` v6→v7 — there is no agent deliverable. Dependabot opens the PR
on its schedule. Opening a triage→agent track duplicates that automation and
generates recurring noise, since the loop re-reports the same finding each run
until Dependabot lands it.

These findings are closed as `wontfix`, not actioned. The staleness audit's value
is the complement: pins Dependabot does *not* cover (language runtimes, container
base images, CI matrix versions, EOL jumps). Those remain in scope.

**Bar to revisit:** A finding inside Dependabot's scope becomes actionable only if
the corresponding Dependabot PR is demonstrably held open / stuck (config broken,
PR failing CI for an unrelated reason, or auto-merge disabled and the PR ignored).
In that case file a tracked issue about the *Dependabot pipeline*, not the bump.

## Prior requests

- #385 — staleness-review: CI action pin actions/checkout v6→v7 (Dependabot-deferred)
