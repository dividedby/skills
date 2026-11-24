# Repo-audit asks once before running untrusted code

> **Status: Accepted** — maintainer decision (2026-11-21). **Amends [ADR 0042](./0042-repo-audit-becomes-a-read-only-report.md).**

> **Amended 2026-11-23** — maintainer decision, [dividedby/skills#666](https://github.com/dividedby/skills/issues/666): a fork of a third-party repo is untrusted unless it is in the index, and a repo with no remote is trusted but its fleet-standards section is Not assessed. The Decision and Consequences below state the amended rules.

## Context

ADR 0042's read-only rule protects the audited repo from the audit. Nothing
protects the machine and the session from the repo. Stage 2 runs the repo's tests
and builds and starts the app; the baseline adds scanners and the repo's own gate
commands, and a fresh-clone install follows. Each is arbitrary code running with
the user's permissions and network access. That is acceptable for the
maintainer's own repos. `repo-audit` now aims at any repo, which includes a fork,
a dependency, a candidate to adopt and a contributor's project.

The fleet-standards section has the same gap: its rows are the maintainer's house
rules, and they do not apply to a repo the maintainer does not own.

## Decision

- **Ownership test.** Stage 1 records the test's result: pass, fail or no remote.
  A repo with no remote (local only) gets no remote. Otherwise the test passes
  when the repo's GitHub owner is the authenticated user or an org that user
  belongs to and the repo is not a fork of a third-party repo (a fork passes this
  leg only when its source repo's owner also passes it), or when it is listed as a
  fleet repo; the index is the only way a third-party fork passes. Anything else
  fails. A repo is trusted when the test passes, when the result is no remote, or
  when the user's prompt says it is trusted or its code may run; otherwise it is
  untrusted. A prompt override trusts the repo for execution only: it does not
  make it a fleet repo.
- **Ask once per run.** When the repo is untrusted, the main session asks the user
  one question before any of the repo's code runs: may this run execute it? The
  question lists what would run: tests, builds, the app, the repo's gate
  commands, scanners that execute repo code and a fresh-clone install.
  - **Yes:** the code runs inside the Execution boundary, from a scratch clone of
    the pinned commit, for this run only.
  - **No, or no answer:** the run does not execute the repo's code. A run that
    cannot ask (unattended, or reporting to another session) does not ask and
    takes No; a question nobody answers is No. Static reading and scanners that
    do not execute repo code still run. Every skipped method is "Untrusted not
    run", and an area whose applicable methods all needed execution is Not
    assessed with that reason.
- **Fleet standards.** The same ownership result decides whether the section
  applies. A repo that passes it is checked; a repo with no remote gets "Not
  assessed (Needs X: a remote)"; a repo that fails it gets "n/a (not a fleet
  repo)". No row runs for the last two.
- **Record.** The answer and its time go in the run log; the page states which
  way it went and names the areas it cost.
- **Failure condition.** Code from an untrusted repo executed without a yes for
  this run, or outside the Execution boundary or not from a scratch clone, fails
  the audit.
- **Unchanged.** The read-only rule, the Execution boundary's contents, the
  lenses, the stages and the rubric's areas.

## Consequences

- A run on a repo the maintainer does not own pauses once, early, for an answer.
  Saying in the prompt that the repo's code may run skips the question.
- An unattended run on such a repo is a static audit. Its run-based areas read
  "Not assessed (untrusted, not run)" instead of a verdict.
- The ownership test needs `gh` to say who the user is. When it cannot, the repo
  fails the test and is asked about, never trusted by default.
- A fork of a third-party repo is untrusted unless it is in the index, even when
  the user owns the fork: its code is someone else's. A scratch repo with no
  remote runs without the question, and its fleet-standards section is Not
  assessed.
- Fleet-standards fails cannot exist for a repo that is not a fleet repo.
