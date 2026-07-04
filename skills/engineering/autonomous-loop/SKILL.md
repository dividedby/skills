---
name: autonomous-loop
disable-model-invocation: true
description: >
  Turn a briefed backlog into a safely-running unattended agent loop.
---

# Autonomous Loop

This skill turns a briefed backlog into a safely-running **autonomous loop** —
an unattended agent run that repeats a work cycle until a stop condition. It is
**methodology, not a runtime**: it teaches which existing runtime to wire up and
the discipline that makes running unattended safe. See `CONTEXT.md` for the
**Autonomous loop** / **Proposal loop** / **Run-book** vocabulary, and
[RUNNING-AFK.md](RUNNING-AFK.md) for the HITL→AFK hardening detail.

Deferrals: spec/backlog authoring → `/to-issues` and `/triage`; durable
TDD-ready issue bodies → `/software-design`; loop runtime mechanics → `/loop`
or `/schedule`/CI-cron. This skill checks input durability (element 5) and owns
the five elements below — it never authors the backlog or builds a new runtime.

## Select the runtime (don't build one)

- **`/loop`** — interactive or self-paced, you're around to watch. Good for the
  HITL phase and short burndowns.
- **`/schedule` or CI-cron `claude -p`** — recurring and unattended. The CI-cron
  form is what this repo dogfoods; a fresh `claude -p` per run makes the
  iteration boundary a context boundary for free.
- **One-shot serialized burn-down** — a finite run to completion over a fixed
  backlog (how #64→#66 ran). Stops when the backlog empties.

Per-item sub-agent dispatch and flush/drop mechanics: [FIREWALL.md](FIREWALL.md).

## What this skill owns

### 1. Stop condition

State an unambiguous halt before starting: backlog empty, N iterations done, a
cost ceiling hit, or a gate stays red.

### 2. Per-iteration feedback gate

Each iteration must pass its own gate — tests, lint, typecheck, build — or
**halt without committing**. A red gate never lands work. On a pass, print a
single deterministic marker per check, not the full tool output — reserve full
output for the failing check, so the gate itself doesn't become a
context-rot source over many unattended iterations.

### 3. HITL→AFK by graduation-by-guardrail

You earn unattended running by **guardrails, not observation time**. Graduate
only when all four hold (detail in [RUNNING-AFK.md](RUNNING-AFK.md)):

1. A **deterministic guard** blocks irreversible ops — the **#64 git-guard**
   (`.claude/hooks/git-guard.py`) is the worked exemplar, sequenced first to
   harden the loop that then burned down #66.
2. Work lands on **branches/PRs, never `main`**.
3. Every iteration **passes its gate or halts** (element 2).
4. An **iteration / cost / time cap** bounds the run (lived caps: backlog size,
   `total_cost_usd`, CI `timeout-minutes`).

**Applying loops are first-class.** Committing, opening PRs, and merging on a
green gate are in scope (the #64→#66 burn-down). Per-item close-out uses
`/flow-pr` — the **apply-and-merge-on-green** end of the gate spectrum, bound by
guardrails 2–4 above. **Propose-only**
([ADR 0003](../../../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md))
is the *strictest* point on the spectrum, for when unsupervised applying is
unacceptable — not the universal rule. Gate spectrum detail and `/flow-pr`
wiring: [RUNNING-AFK.md § The gate spectrum](RUNNING-AFK.md).

### 4. Monitor, stop, resume

The loop writes a durable **progress file** (flush/drop mechanics:
[FIREWALL.md](FIREWALL.md)). It lets you watch progress, stop cleanly, and
resume by reading the file and skipping done items.

### 5. Brief-durability precondition

A **pre-run shape check**, run once before the first iteration: check each brief
survives a cold pickup per the **Durability** criteria `/software-design` enforces
— names are behaviours/interfaces/types (not file paths or line numbers),
acceptance criteria state *what* in observable Given/When/Then form (not *how*
via implementation steps) and are independently verifiable, scope boundary
explicit where non-obvious. A brief that fails bounces back to its author
(`/software-design` owns this format) — this skill gates durability, it never
authors the brief.

This is **distinct from per-item reconciliation**, which runs inside the
firewalled sub-agent at each item's pickup: the sub-agent reads the live full
issue body + comments and halts on a material discrepancy against the brief (see
**Reconcile the brief against the live issue first** in
[RUNNING-AFK.md](RUNNING-AFK.md)). Element 5 checks the brief's *shape* once;
reconciliation checks its *currency against the live issue* every pickup.

### 6. Non-binary-quality evaluator gate

Element 2's gate is binary — tests pass or the loop halts. When work is
subjective or under-specified enough that a mechanical pass can still be wrong
quality, split the iteration into a **generator pass** and a cold **evaluator
pass** scored against a rubric. Default to the binary gate; reach for the split
only when it demonstrably misses quality failures. Mechanics — generator/evaluator
split, rubric design, calibration, sprint contracts, cost heuristics:
[EVALUATOR-GATE.md](EVALUATOR-GATE.md).
