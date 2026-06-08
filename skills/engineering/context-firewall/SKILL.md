---
name: context-firewall
description: >
  Restructure a long, multi-item agent run so output quality doesn't decay as
  the context window fills — handle each item in a fresh, discarded sub-agent
  context, with between-item budget checkpoints and intentional compaction.
  Use when a single long run degrades its late items, blows past its window or
  time budget, or you want to decompose a monolithic run. Applies whether or
  not a loop wraps the run; the motivating case is one loopless monolithic run.
---

# Context Firewall

A long run that processes many items in **one** context degrades the items it
reaches late: once the window fills past its **smart zone**, recall blurs,
instructions get dropped, and the harness eventually forces a lossy mid-stream
compaction. This skill restructures the run so each item gets a clean context
and the orchestrator stays lean across the whole run.

It applies to **any** long multi-item run — most importantly a **single
monolithic run with no loop at all** (the motivating case: `agent-research`'s
daily synthesis distilling every stale source in one context). A loop is one
optional wrapper, not a prerequisite. When a loop *does* wrap the run,
`/autonomous-loop` points in here for per-iteration hygiene; this skill stands
alone without it. [FIREWALL-PATTERNS.md](FIREWALL-PATTERNS.md) carries the
sub-agent firewall shapes, budget-checkpoint placement, and compaction mechanics.

---

## Vocabulary

- **Work item** — one briefed, independently-runnable chunk with its own inputs
  and a compact result. The shared unit with `/autonomous-loop`; what you firewall.
- **Context firewall** — a fresh sub-agent context that loads only one work
  item's inputs, returns a compact result, and is discarded before the next.
  Raw work never reaches the orchestrator.
- **Smart zone** — the early span of a context window where recall and
  instruction-following are sharp. Quality decays as a run pushes past it.
- **Budget checkpoint** — a proactive between-items headroom check that acts
  *before* the harness's forced, lossy auto-compaction would fire.

---

## When to Skip

- A short run that finishes well inside its smart zone — no firewall needed.
- A single-item task with no repeatable per-item unit to extract.
- Loop *setup* questions (HITL→AFK, iteration caps, monitor/stop/resume) —
  that is `/autonomous-loop`. This skill owns within-run context shape only.

---

## Workflow

### 1. Identify the per-item unit

Find the repeatable **work item**: the chunk processed once per pass with
**independent inputs** and a compact, mergeable result. If items share mutable
state or need full ordered history they aren't independent — say so rather than
forcing a firewall that loses needed context.

### 2. Firewall each item in a fresh sub-agent context

Dispatch each work item to a sub-agent (the existing Agent/sub-agent
mechanism — **no new runtime**) that loads only that item's inputs and
returns a compact result. The orchestrator never sees the raw work, only the
distilled return. This is **within-item** hygiene: per-item bloat is discarded
with the sub-agent. In a session — the Claude Code CLI, interactive or under
`/loop` — that sub-agent is an **in-session sub-agent** (the Agent tool, no new
process), *not* a `claude -p`: you're already in a session, so use it. The
`claude -p` firewall-per-item is the **headless-process** case, where there is no
session to dispatch within (CI, cron, runners) — there a fresh process per run
gives the boundary for free; a single interactive session or a monolithic run
does not, so the in-session sub-agent supplies it. See
[FIREWALL-PATTERNS.md](FIREWALL-PATTERNS.md).

### 3. Budget checkpoint between items

Between items, check remaining headroom *before* continuing. Acting at a clean
boundary beats the harness's forced mid-stream compaction, which is lossy and
lands arbitrarily. If headroom is low, compact (step 4) or stop and resume fresh.

### 4. Intentionally compact between items

At a clean between-items boundary, **flush accumulated results to a durable
progress artifact, then drop them from context** and continue lean. This is
**across-item** hygiene: it bounds orchestrator bloat, the complement to the
per-item firewall. Dropping in-context state is safe *because* it is persisted —
this is the **same progress artifact** `/autonomous-loop` uses for monitor/stop/resume.

---

## Anti-Patterns

- **One context for the whole run.** The default that decays late items —
  firewall the repeatable unit instead.
- **Compacting only at the end.** Compact between items, proactively, not once
  the window is already full.
- **Letting raw sub-agent work back into the orchestrator.** Return a compact
  result; the firewall is wasted if the orchestrator re-absorbs the detail.
- **Reaching for this on loop setup.** Caps, gates, and HITL→AFK are
  `/autonomous-loop`.
