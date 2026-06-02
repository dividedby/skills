# Running AFK

Detail for [SKILL.md](SKILL.md): how to harden a loop until it can run
unattended, and how to watch and stop it once it does. **Illustrative
sketches** (ADR 0002), not a fixed procedure — adapt to the loop in front of
you.

## Graduation-by-guardrail, expanded

You do not earn AFK by watching a loop behave for an hour. Observation proves
nothing about the run you *didn't* watch. You earn it by making the bad outcomes
**structurally impossible or bounded**. The four guardrails, with the why:

### 1. A deterministic guard blocks irreversible ops

A hook — not the model's judgment — refuses the operations you can't take back:
force-push, `reset --hard`, branch deletion, `clean -f`, discard-style
checkout/restore. The model can be wrong; the guard can't be talked out of it.

The worked exemplar is this repo's **#64 git-guard** (`.claude/hooks/git-guard.py`),
a PreToolUse Bash guard that hard-blocks destructive git with exit 2 while
leaving normal commit/push/`checkout -b` untouched. It was sequenced **first**,
on purpose: harden the loop, *then* let it burn down #66 unattended. That
ordering is the pattern — install the guard before you walk away, not after the
first incident.

### 2. Work lands on branches/PRs, never `main`

Every iteration's output is a branch and a PR, never a direct commit to the
default branch. This keeps the blast radius reviewable and revertible: a bad
iteration is a closed PR, not a rewritten history. Pair it with the guard in (1)
so the loop *cannot* route around the branch.

### 3. Every iteration passes its gate or halts

The per-iteration feedback gate (SKILL.md, element 2) is a graduation
requirement, not just good practice: an AFK loop with no gate applies unverified
work at machine speed. Red gate → halt, don't commit. A loop that commits
through red is disqualified from AFK no matter how good the other guardrails are.

### 4. An iteration / cost / time cap bounds the run

Every unattended run has a hard ceiling so a stuck or looping agent stops
itself. Three lived cap types in this repo:

- **Iteration / backlog size** — finite work; the loop ends when the backlog
  empties or N iterations elapse.
- **Cost** — `total_cost_usd` (captured per run, #63) gives a dollar ceiling.
- **Wall-clock** — CI `timeout-minutes` kills a run that overruns.

Pick at least one; for genuinely unattended runs, prefer a cost or time cap that
fires even if the iteration counter never advances (the stuck-in-a-loop case).

## The gate spectrum

Guardrail (2) is one point on a spectrum of how much an iteration is trusted to
*apply*:

- **Propose-only** (strictest) — never commits; emits labeled issues for a human
  to decide ([ADR 0003](../../../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md)).
  For when unsupervised applying to a shared artifact is unacceptable (the
  Proposal-loop family).
- **Apply-on-branch** — commits and opens PRs, never merges; a human merges.
- **Apply-and-merge-on-green** — merges its own PR when the gate passes (the
  #64→#66 burn-down).

Applying loops are first-class. Choose the strictest point that still lets the
loop do its job — not propose-only by default.

## Monitor, stop, resume

The **progress file** is the shared spine (the same artifact `/context-firewall`
flushes to). It is what makes a long unattended run observable and recoverable.

- **Monitor** — the loop appends each completed item's compact outcome. Tail the
  file (or the PRs it opens) to see progress without attaching to the run.
- **Stop** — a clean stop happens at an iteration boundary after a flush, so no
  half-done item is lost. A cap (guardrail 4) is the automatic stop; a manual
  stop is just ending the run between iterations.
- **Resume** — restart by reading the progress file and skipping done items.
  Because every landed item is persisted before the next begins, resume is
  idempotent — never redoing or double-applying completed work.

A loop you can't stop or resume isn't ready for AFK. Wire the progress file
before the first unattended run.
