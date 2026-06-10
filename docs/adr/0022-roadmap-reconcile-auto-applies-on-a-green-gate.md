# Roadmap reconcile auto-applies (branch → PR → auto-merge on a green gate); closes stay human

[ADR 0017](./0017-doc-regen-write-posture.md) made the roadmap skill (`doc-regen`,
renamed to `roadmap` — see #200) **propose-only**: it edits the working tree and
never commits, a human reviews `git diff` and commits, and a loop suppresses even
the additive issue writes. In practice the reconcile edit is **mechanical and
low-stakes** (a census projection of live `gh` state), and prompting the
maintainer to review-and-commit every reconcile is friction with no payoff. The
maintainer asked to stop being prompted: reconcile should land its own changes.

## Decision

Reconcile **auto-applies its roadmap edits** rather than leaving them for manual
review:

1. **Branch → commit → PR → auto-merge on a green gate.** Reconcile writes to a
   branch, opens a PR, and enables **auto-merge** so GitHub merges once the repo's
   checks pass (hook self-tests, `check-skill-registration`, any CI). The PR is the
   audit trail; the green gate is the safety, not a human click. Never a direct
   push to the default branch.
2. **What auto-applies**: the roadmap edits — Tier-1 mechanical repairs, the
   burn-down recompute, Tier-2 additive row slotting — plus additive issue comments.
3. **Closing issues stays human, but agent-powered.** Tier-3 is *upgraded* from a
   passive "looks done" note to an **active doneness investigation** — the agent
   checks the linked PRs, the code, and the plans to answer "are we done?" and
   surfaces a confident recommendation. It still **does not close**: closing on
   inference is the one irreversible act kept behind a human. Likewise, issue
   **body rewrites** stay out of scope.
4. **Applies in both interactive and loop runs.** This **reverses ADR 0017's
   loop-suppression invariant** for reconcile: the posture is the same whether a
   human is watching or not, because the green gate — not a watching human — is the
   control. This is an **applying loop** in the sense the `autonomous-loop` skill
   already blesses (commit/PR/merge on a green gate), not a proposal loop.

## Why this does not reopen ADR 0003

[ADR 0003](./0003-skill-improvement-workflows-propose-via-issues.md) governs
**proposal loops** that emit *speculative improvements* (apply-agent-research,
arch-review) — those stay propose-only. Reconcile is **deterministic maintenance**
of the maintainer's own roadmap, gated on green checks; applying it unattended is
categorically different from auto-applying a judgment proposal. The propose-only
rule is untouched for the proposal-loop family.

## Consequences

- ADR 0017 is **amended**: its "never commits" line and loop-suppression invariant
  no longer hold for the reconcile path; its no-auto-close and no-body-rewrite
  invariants **do** still hold (now the agent-powered-but-human-gated close).
- The green gate is load-bearing — a repo wiring this must have the hook self-tests
  (and any CI) actually run on the reconcile PR, or auto-merge has nothing to gate.
