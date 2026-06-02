# Firewall Patterns

Detail for [SKILL.md](SKILL.md): concrete shapes for the sub-agent firewall,
where budget checkpoints go, and how intentional compaction works. These are
**illustrative sketches** (ADR 0002), not literal procedures — adapt them to
the run in front of you.

## Sub-agent firewall shapes

The firewall is always the same move: spend the raw, bulky work inside a
context you will throw away, and let only a distilled result cross back. Three
common shapes:

- **Read-and-distill.** The item's inputs are large (a long source document, a
  sprawling file tree, a noisy log). The sub-agent reads them and returns a
  short structured summary — the facts the orchestrator needs, not the raw
  material. The motivating `agent-research` synthesis is this shape: one
  sub-agent per stale source, each returning distilled knowledge.
- **Do-and-report.** The item is a unit of work (refactor one module, triage
  one issue, implement one ticket). The sub-agent does the work, runs its own
  checks, and reports a compact outcome (what changed, pass/fail, follow-ups) —
  the orchestrator never carries the intermediate edits or tool output.
- **Fan-out-and-merge.** Items are independent enough to run in parallel
  sub-agents. Each returns its compact result; the orchestrator merges the
  results, never the raw work. Only safe when items truly don't share mutable
  state.

What makes it a firewall, in every shape: the **return is compact and the raw
work is discarded with the sub-agent**. If the orchestrator re-reads the same
inputs after the sub-agent returns, you built a detour, not a firewall.

### Keep the return compact

- Specify the return shape up front (a heading set, a fixed schema, a bound on
  length). An unconstrained sub-agent returns as much as a non-firewalled run.
- Return conclusions and pointers, not transcripts. "Updated `auth.ts`; 3 tests
  green; one TODO filed" — not the diff and the test log.
- Push file-path-level detail into the durable artifact, not the return, when
  the orchestrator only needs to know an item is done.

## Budget-checkpoint placement

A budget checkpoint is a **between-items headroom check** that fires before the
harness's forced auto-compaction would. Placement:

- **At each item boundary** for long runs — the natural clean point, after a
  result is flushed and before the next item loads.
- **Before a known-heavy item** — if the next item's inputs are large, check
  first rather than discovering the overflow mid-item.
- **Never mid-item.** A checkpoint that interrupts an item splits its context
  exactly where you wanted it whole. The whole point of the firewall is that
  item work is atomic.

What the checkpoint decides: enough headroom → continue; low headroom →
intentionally compact (below); near-exhausted with items left → stop and resume
fresh against the progress artifact. The cap itself (how many items, what cost
ceiling, what wall-clock limit) is `/autonomous-loop`'s concern when a loop
wraps the run — the checkpoint just reads headroom and reacts.

## Compaction mechanics

Intentional compaction trades in-context state for persisted state at a clean
boundary:

1. **Flush** — append the items completed so far (their compact results) to the
   durable progress artifact: a `PROGRESS.md`, a results file, the issue
   tracker, whatever survives the run. This is the **same artifact**
   `/autonomous-loop` reads for monitor/stop/resume.
2. **Drop** — clear the flushed detail from the working context. Keep only what
   the remaining items genuinely need: the spec, the stop condition, and a
   pointer to the artifact.
3. **Continue lean** — resume from the next item with a near-empty orchestrator.

Why this beats the harness's forced compaction: you choose the boundary (clean,
between items) and you choose what survives (the distilled artifact you wrote on
purpose). The forced version fires mid-stream at an arbitrary point and keeps
whatever heuristic it keeps — lossy and unpredictable for exactly the late items
this skill exists to protect.

### Resume safety

Because every completed item is in the artifact before its detail is dropped, a
stopped or crashed run resumes by reading the artifact and skipping done items.
Dropping in-context state is only safe once the flush has happened — flush
first, drop second, never the reverse.
