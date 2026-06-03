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

## Worked example: a triaged backlog in one self-paced session

The common case where this skill and `/context-firewall` compose. You have a
backlog of briefed, ready-for-agent issues and you want to burn it down from a
single interactive session (`/loop` self-paced) rather than a scheduled
fresh-process-per-issue runtime. Because it's **one accumulating context**, the
firewall is what keeps the last issue as sharp as the first.

1. **Input** — the triaged backlog (authored by `/triage` / `/to-issues`, not
   here). Each issue is one **work item**.
2. **Runtime** — `/loop` self-paced. One session, you're around for the first
   passes. The iteration boundary is *not* a context boundary here — the
   orchestrator fills as issues accumulate — so step 4 supplies the boundary.
3. **Stop condition** — backlog empty, or a cap trips first (below).
4. **Firewall each issue** (`/context-firewall`) — dispatch each issue to a
   sub-agent (the in-session Agent/sub-agent dispatch, *not* a new process) that
   loads only that issue's brief, does the work behind its own gate, and returns
   a compact outcome. The loop session never carries the raw diffs or tool
   output — only the distilled result.
5. **Gate or halt** — the sub-agent runs the issue's feedback gate; a red gate
   halts that item without landing work. Green → it opens a branch + PR
   (guardrail 2), never `main`.
6. **Flush, then drop** — append the completed issue's outcome to the progress
   file, drop its detail from the session, continue lean. This is the same
   progress file that makes monitor/stop/resume work.
7. **Cap** — backlog size is the natural ceiling; add an iteration or
   wall-clock cap so a stuck issue can't spin forever (guardrail 4).

The guardrails are what let steps 4–6 run while you step away: the git-guard
(guardrail 1) blocks irreversible ops no matter what a sub-agent decides, and
every item is on a PR, gated, and persisted before the next begins.

When *would* you skip `/context-firewall` in this flow? When the runtime is
already fresh-context-per-issue (a scheduled `claude -p` per issue) — there each
process is its own firewall and the orchestrator never accumulates. The firewall
earns its keep precisely because the single-session runtime doesn't give it for
free.
