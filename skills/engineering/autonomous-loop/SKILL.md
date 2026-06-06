---
name: autonomous-loop
description: >
  Take a briefed backlog to a safely-running unattended ("AFK") agent loop —
  the discipline around running an agent unattended, not a runtime. Owns the
  stop condition, per-iteration feedback gates, the HITL→AFK graduation with an
  iteration/cost/time cap, and monitor/stop/resume. Use when setting up or
  running a loop over a backlog, running an agent while away, or hardening a
  loop so it can run unattended. Applying loops (commit / open PRs / merge on a
  green gate) are first-class; propose-only is the strict end of the spectrum.
---

# Autonomous Loop

This skill turns a briefed backlog into a safely-running **autonomous loop** —
an unattended agent run that repeats a work cycle until a stop condition. It is
**methodology, not a runtime**: it teaches which existing runtime to wire up and
the discipline that makes running unattended safe. See `CONTEXT.md` for the
**Autonomous loop** / **Proposal loop** / **Run-book** vocabulary, and
[RUNNING-AFK.md](RUNNING-AFK.md) for the HITL→AFK hardening detail.

It owns five things and **defers the rest**:

- **Input** — a briefed backlog is the *input*, not something this skill
  authors. Defer spec/backlog authoring to `/to-issues` and `/triage`, and
  durable TDD-ready issue bodies to `/software-design` (`issue-shape.md`).
  This skill only *checks* the input is durable (element 5); it never authors it.
- **Execution** — defer to an existing runtime (below). No new loop mechanism.
- A loop iteration that is **itself multi-item** → reach for `/context-firewall`
  for per-item context hygiene. (One-way pointer; the **work item** is the
  shared unit, and both share the durable **progress file**.)

---

## Select the runtime (don't build one)

Match the runtime to the run; teach selection, not a new mechanism:

- **`/loop`** — interactive or self-paced, you're around to watch. Good for the
  HITL phase and short burndowns.
- **`/schedule` or CI-cron `claude -p`** — recurring and unattended. The CI-cron
  form is what this repo dogfoods; a fresh `claude -p` per run also makes the
  iteration boundary a context boundary for free.
- **One-shot serialized burn-down** — a finite run to completion over a fixed
  backlog (how #64→#66 ran). Stops when the backlog empties.

---

## What this skill owns

### 1. Stop condition

Every loop needs an unambiguous halt: backlog empty, N iterations done, a cost
ceiling hit, or a gate stays red. State it before starting. A loop with no stop
condition is the failure mode this skill exists to prevent.

### 2. Per-iteration feedback gate

Each iteration must pass its own gate — tests, lint, typecheck, build — or
**halt without committing**. A red gate never lands work. The gate is what makes
unattended iteration trustworthy; without one, AFK is reckless regardless of
caps.

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

**Applying loops are first-class** — committing, opening PRs, and merging on a
green gate are in scope (the #64→#66 burn-down). **Propose-only**
([ADR 0003](../../../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md))
is the *strictest* setting on the gate spectrum, for when unsupervised applying
is unacceptable — not the universal rule.

### 4. Monitor, stop, resume

The loop writes a durable **progress file** (the same artifact
`/context-firewall` flushes to). It lets you watch progress, stop cleanly, and
resume by reading the file and skipping done items. Persisted progress is what
makes stopping safe.

---

### 5. Brief-durability precondition

This is a **pre-run shape check**, run once before the first iteration: check
each brief survives a cold pickup per the **Durability** criteria in
[issue-shape.md](../software-design/issue-shape.md) — names are behaviours/
interfaces/types (not file paths or line numbers), acceptance criteria state
*what* in observable Given/When/Then form (not *how* via implementation steps)
and are independently verifiable, scope boundary explicit where non-obvious. A
brief that fails bounces back to its author (`/software-design`'s `issue-shape.md`
owns this format) — this skill gates durability, it never authors the brief.

It is **distinct from per-item reconciliation**, which is a separate,
*per-pickup* responsibility done inside the firewalled sub-agent: at each item's
pickup the sub-agent reads the live full issue body + comments and halts on a
material discrepancy against the brief (see [RUNNING-AFK.md](RUNNING-AFK.md) step
4a). Element 5 checks the brief's *shape* once; reconciliation checks the brief's
*currency against the live issue* every pickup. Don't conflate them.

---

## Anti-Patterns

- **Building a loop runtime.** Select `/loop`, `/schedule`/CI-cron, or a
  one-shot burn-down — don't reimplement one.
- **Authoring the backlog here.** Defer to `/to-issues` / `/triage`.
- **AFK on observation time alone.** Graduate by guardrails, not by "it looked
  fine for a while."
- **Committing on a red gate.** Halt instead — always.
- **No cap.** An unbounded unattended loop is the thing to never ship.
