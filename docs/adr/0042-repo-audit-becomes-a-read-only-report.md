# Repo-audit becomes a read-only report

> **Status: Accepted** — maintainer decision (2026-10-27). **Supersedes the 2026-10-12 `repo-audit` amendment in [ADR 0041](./0041-council-drops-peer-rank-and-runs-selector-inline.md).**

> **Amended by [ADR 0045](./0045-repo-audit-checks-fleet-standards-read-fresh.md)** — the main session also checks the repo against the fleet standards in `dividedby/claude-config`, read fresh each run; the read-only rule, lenses and stages are unchanged.

> **Amended by [ADR 0046](./0046-repo-audit-types-tiers-and-a-fallback.md)** — the profile adapts to the repo's type, size and shape (types, size tiers, a fallback, monorepos, no GitHub remote); the read-only rule, lenses and stages are unchanged.

> **Amended by [ADR 0047](./0047-repo-audit-asks-once-before-running-untrusted-code.md)** — a repo the maintainer does not own is untrusted: the run asks once whether it may execute the repo's code, and without a yes it does not; the fleet-standards section applies only to fleet repos; the read-only rule, lenses and stages are unchanged.

> **Amended by [ADR 0048](./0048-repo-audit-keeps-isolated-instances-up-and-probes-the-ui.md)** — Stage 2 starts a web UI's isolated instances and probes it with Playwright, and both instances stay up through Stage 3 (replacing the stop-the-server step); the read-only rule and lenses are unchanged.

> **Amended by [ADR 0049](./0049-repo-audit-lens-roster-depth-levels-and-budgets.md)** — five lenses in one launch, at most four at `standard`, each with an agent type, model and tools; Market off for private and single-user repos; `quick` and `standard` depth with stated budgets; the read-only rule and stages are unchanged.

## Context

`/repo-audit` (3.1.0) ran a leverage hunt: up to five lens seats on the Workflow
tool, a synthesis agent that verified findings at their cited paths, then
reconciliation against the open backlog, epics, a roadmap and `to-tickets`
decomposition. Its output was GitHub issues.

A different shape was tried by hand on an app repo (2026-10-26): four parallel
lens agents — code and performance with measured benchmarks, architecture/repo/
docs, design against the platform's guidelines with screenshots and a mockup
spec, and outside research — then the main session re-checking every high
finding at its source, and one private report page with verdicts, a Now/Next/
Later plan, screenshots, rendered mockups and a "what was checked" list. It
changed nothing in the repo. The maintainer judged the result better than the
leverage hunt's and asked for it to replace the skill.

What the hand run did that the leverage hunt did not:

- **Measured.** Timings came from a scratch benchmark, so the plan's order
  rested on numbers, and projections were labelled as such.
- **Saw the product.** Design findings came from screenshots of a demo build
  and ended in mockups, not adjectives.
- **Verified in the main session.** Two lens claims were corrected before
  publishing (a severity lowered for context the lens lacked; a research claim
  contradicted by the code, shown with both readings).
- **Left the decision with the maintainer.** A plan to pick from, read in the
  morning, instead of issues filed overnight.

## Decision

`repo-audit` is rewritten as a read-only audit that publishes one report page.

- Six stages: scope, capture, lenses (parallel), verify, plan and mockups,
  publish. The audited repo is never changed; any change is a failed audit.
- Four lenses, run with the Agent tool in one parallel launch. Design runs only
  for projects with a UI; market only where there is a field to compare.
- The main session verifies every High finding, and every finding the "Now"
  column rests on, before the page is built. ADR 0041's grounding principle
  (verification beats cross-review) carries over; the synthesis agent does not.
- Output is a private Artifact built from `template.html`, a supporting file in
  the skill folder; where the Artifact tool is unavailable, the page is sent as a
  file.
- Issue filing leaves the skill. A maintainer who wants issues runs
  `/to-tickets` on the plan.

`playbook.md` is replaced by `briefs.md`, one brief per lens.

## Consequences

- **Breaking.** `/repo-audit` no longer reconciles the backlog, writes epics or
  a roadmap, or creates, rewrites or closes issues. The 3.1.0 skill remains in
  git history at the release commit `d95ab6f`.
- A skill folder now holds a non-markdown supporting file. `CONTEXT.md`'s
  **Supporting file** definition widens to cover it.
- The skill no longer drives the Workflow tool. ADR 0036's decision that skills
  _may_ do so stands; `/council` still does.
- A run costs four lens agents at most plus main-session verification, against
  six agents before; the design lens runs on opus.
- Screenshots need a demo or sample-data build. Projects without one get a
  design lens that works from source and states that it saw no screens.
