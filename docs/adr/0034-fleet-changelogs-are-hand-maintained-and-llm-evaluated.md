# Fleet changelogs are hand-maintained and LLM-evaluated, not semantic-release

> **Status: accepted** — ratified via PR [#460](https://github.com/dividedby/skills/pull/460) (closing [#456](https://github.com/dividedby/skills/issues/456)). Records the fleet decision from spike [#454](https://github.com/dividedby/skills/issues/454) (drained from the Idea Inbox, maintainer request 2026-06-24). Extends [#397](https://github.com/dividedby/skills/issues/397) fleet-wide; does not overturn it. Records the decision only — the evaluator loop ([#457](https://github.com/dividedby/skills/issues/457)), the 2.0.0 migration of the existing six ([#458](https://github.com/dividedby/skills/issues/458)), and seeding the missing six ([#459](https://github.com/dividedby/skills/issues/459)) are downstream.

Every fleet repo keeps its `CHANGELOG.md` **hand-maintained** in
[Keep a Changelog 2.0.0](https://keepachangelog.com/en/2.0.0/) form, against the
shared rubric in [`docs/agents/changelog-guideline.md`](../agents/changelog-guideline.md).
Upkeep and the quality bar are enforced by a **weekly per-repo LLM-evaluator**
that reads `git log` since the last changelog entry and **flags** weak or missing
entries — a nudge, never a blocking gate. We **reject semantic-release** and
commit-convention-driven changelog generation.

**semantic-release is a release-pipeline gate — it fails the maintainer's hard
constraint.** [#454](https://github.com/dividedby/skills/issues/454) set an
explicit anti-gate constraint: changelog health is enforced "at most a weekly
per-repo job that evaluates… not a blocking check." semantic-release is
fundamentally the opposite — it runs in CI on the release branch, derives the
next version from commit messages, and gates the publish pipeline on that
analysis. Adopting it would put a blocking check on the critical path of every
release, which is the one shape the maintainer ruled out.

**Its changelog generation is not cleanly modular.** semantic-release couples
changelog output to the whole automated-versioning-and-publish chain (commit
analysis → version computation → git tag → registry publish → release notes).
There is no clean seam to take only the "write a changelog" behavior without also
buying conventional-commits enforcement and automated releases. The fleet wants
the changelog, not the pipeline.

**Fleet-wide conventional-commits discipline is unwarranted.** Generation only
works if every commit on every repo carries a parseable conventional-commit type.
That taxes each commit across a small, single-maintainer-plus-agents fleet for a
payoff — an auto-assembled changelog — we get more cheaply from a weekly
evaluator that reads ordinary `git log`. The commit-message tax does not pay off
at this scale.

**Generation fights the quality bar; hand-maintenance protects it.** The rubric's
core rule is audience-first: one line per *notable* change, phrased for a
downstream consumer, not a commit replay. Commit-driven generation produces
exactly the git-log dump the standard warns against — KaC 2.0.0 itself moved its
tagline to "Clearly document the evolution of your projects," away from 1.x's
"Don't let your friends dump git logs into changelogs." A human (or an agent
writing the entry at merge time) selects and phrases; a generator transcribes.
The evaluator preserves this by judging quality and flagging — it does not author
or rewrite, so the audience-first voice is never delegated to a transcriber.

**Reconciliation with [#397](https://github.com/dividedby/skills/issues/397).**
#397 settled *hand-maintained, no automation, Keep-a-Changelog format* for the
skills repo and explicitly deferred the cross-repo concern ("fleet concern, not
this repo"). This ADR is that deferred follow-up. It **extends** #397's choice to
every fleet repo and layers on a non-blocking quality nudge; it does **not**
reverse it. The only deltas to #397's regime are (a) fleet scope, (b) the weekly
evaluator nudge, and (c) the rubric bump from the 1.1.0 convention #397 seeded
against to 2.0.0. Hand-maintenance — the load-bearing choice — is unchanged.

**Rejected alternatives.**

- *semantic-release / commit-convention generation.* A release-pipeline gate
  (violates the anti-gate constraint), not cleanly modular (changelog is welded
  to versioning + publish), and demands fleet-wide conventional-commits for a
  payoff a weekly evaluator delivers from plain `git log`. It also automates
  precisely the commit-replay the rubric forbids.
- *A blocking "changelog entry required" CI check.* Cheaper than semantic-release
  but still a gate the maintainer ruled out — and presence-only: it can confirm
  an entry exists, never that it is notable, consumer-voiced, or correctly
  categorized. The evaluator judges quality; a presence gate cannot.
- *Status quo (per-repo hand-maintenance, no fleet bar).* Leaves the two gaps
  #454 named: no upkeep mechanism (changelogs drift as work ships) and no shared
  quality standard (every repo invents its own bar).

**Boundary.** This ADR ratifies the policy and the guideline doc
([`docs/agents/changelog-guideline.md`](../agents/changelog-guideline.md)). It
implements nothing operational. The evaluator's flag-not-rewrite HITL boundary
and `workflow-authoring.md` conformance (ADR 0019 budget/cadence, ADR 0014
fetched-fresh) are decided and built in
[#457](https://github.com/dividedby/skills/issues/457); migrating the existing
six changelogs to 2.0.0 is [#458](https://github.com/dividedby/skills/issues/458);
seeding the six repos that lack a changelog is
[#459](https://github.com/dividedby/skills/issues/459).
