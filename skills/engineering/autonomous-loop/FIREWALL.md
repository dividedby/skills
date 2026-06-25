# Firewall

Generic context-hygiene discipline for any multi-item run — loop or loopless.
Pointable by any skill that processes more than one item in sequence; no
autonomous-loop context required.

A long run that processes many items in one context degrades the items it
reaches late: once the window fills past its **smart zone**, recall blurs,
instructions get dropped, and the harness eventually forces a lossy mid-stream
compaction. The four elements below keep each item sharp and the orchestrator
lean across the whole run.

---

## Vocabulary

- **Work item** — one briefed, independently-runnable chunk with its own inputs
  and a compact result. What you firewall.
- **Context firewall** — a fresh sub-agent context that loads only one work
  item's inputs, returns a compact result, and is discarded before the next.
  Raw work never reaches the orchestrator.
- **Smart zone** — the early span of a context window where recall and
  instruction-following are sharp. Quality decays as a run pushes past it.
- **Budget checkpoint** — a proactive between-items headroom check that acts
  *before* the harness's forced, lossy auto-compaction would fire.

---

## 1. Identify the per-item unit

Find the repeatable **work item** (defined above). If items share mutable state
or need full ordered history they aren't independent; say so rather than forcing
a firewall that loses needed context.

## 2. Firewall each item in a fresh sub-agent context

Dispatch each work item to a sub-agent (the existing Agent/sub-agent mechanism
— **no new runtime**) that loads only that item's inputs and returns a compact
result. This is **within-item** hygiene: per-item bloat is discarded with the
sub-agent.

Route by environment: when a session exists (interactive), use an **in-session
sub-agent** (Agent tool, no new process). When there is none (CI, cron,
runners), a **headless process** gives the boundary for free. A
builder/architect delegation already *is* a do-and-report firewall — the
remaining job is the orchestrator-side half: the budget checkpoint and
flush/drop in steps 3–4.

### Sub-agent firewall shapes

The move is always the same: spend the raw, bulky work inside a context you will
throw away, and let only a distilled result cross back. Three common shapes:

- **Read-and-distill.** The item's inputs are large (a long source document, a
  sprawling file tree, a noisy log). The sub-agent reads them and returns a
  short structured summary — the facts the orchestrator needs, not the raw
  material.
- **Do-and-report.** The item is a unit of work (refactor one module, triage
  one issue, implement one ticket). The sub-agent does the work, runs its own
  checks, and reports a compact outcome (what changed, pass/fail, follow-ups).
- **Fan-out-and-merge.** Items are independent enough to run in parallel
  sub-agents. Each returns its compact result; the orchestrator merges the
  results, never the raw work. Only safe when items truly don't share mutable
  state.

In every shape, if the orchestrator re-reads the same inputs after the sub-agent
returns, you built a detour, not a firewall.

**Keep the return compact:**

- Specify the return shape up front (a heading set, a fixed schema, a bound on
  length). An unconstrained sub-agent returns as much as a non-firewalled run.
- Return conclusions and pointers, not transcripts. "Updated `auth.ts`; 3 tests
  green; one TODO filed" — not the diff and the test log.
- Push file-path-level detail into the durable artifact when the orchestrator
  only needs to know an item is done.

## 3. Budget checkpoint between items

Between items, check remaining headroom *before* continuing — a clean boundary
beats the harness's forced mid-stream compaction, which is lossy and lands
arbitrarily.

**Placement:**

- **At each item boundary** for long runs — the natural clean point, after a
  result is flushed and before the next item loads.
- **Before a known-heavy item** — if the next item's inputs are large, check
  first rather than discovering the overflow mid-item.
- **Never mid-item.** A checkpoint that interrupts an item splits its context
  exactly where you wanted it whole.

The decision: enough headroom → continue; low → intentionally compact (step 4);
near-exhausted with items left → stop and resume fresh against the artifact.

## 4. Intentionally flush and drop between items

At a clean between-items boundary, **flush accumulated results to a durable
progress artifact, then drop them from context** and continue lean. This is
**across-item** hygiene: it bounds orchestrator bloat, the complement to the
per-item firewall.

1. **Flush** — append the items completed so far (their compact results) to the
   durable artifact: a `PROGRESS.md`, a results file, the issue tracker,
   whatever survives the run.
2. **Drop** — clear the flushed detail from context. Keep only what the
   remaining items genuinely need: the spec, the stop condition, and a pointer
   to the artifact.
3. **Continue lean** — resume from the next item with a near-empty orchestrator.

This beats the harness's forced compaction on both axes: you choose the boundary
(clean, between items) and what survives (the artifact you wrote on purpose),
where the forced version fires mid-stream and keeps whatever heuristic it keeps.

**Resume safety:** because every completed item is in the artifact before its
detail is dropped, a stopped or crashed run resumes by reading the artifact and
skipping done items. Flush first, drop second, never the reverse.

---

## Anti-patterns

- **One context for the whole run.** The default that decays late items —
  firewall the repeatable unit instead.
- **Compacting only at the end.** Compact between items, proactively, not once
  the window is already full.
