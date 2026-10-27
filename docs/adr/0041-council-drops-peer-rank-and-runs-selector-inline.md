# Council drops its peer-rank round and runs the selector inline

> **Status: Accepted** — maintainer decision (2026-10-12). **Amends [ADR 0036](./0036-council-skill-drives-workflow-tool.md).**

> **Superseded in part by [ADR 0042](./0042-repo-audit-becomes-a-read-only-report.md)** — the `/council` decision stands; the 2026-10-12 `repo-audit` amendment is replaced (repo-audit no longer runs a leverage hunt or a synthesis agent).

## Context

`/council` ran about 12 agents per invocation: a selector, five blind seats, five
peer-rank seats and a chair. The peer-rank round is the expensive part, and the
research does not support it as an accuracy gain:

- Multi-agent debate performs about like majority voting at equal compute, and
  seeing peers' rationales can flip a correct answer to a wrong one (conformity).
- LLM judges show position bias, which shuffling the chair's input mitigates.
- Persona selection performs about like random selection, so an agent-run selector
  buys little over a rule.
- The benefit of a jury comes from model-family diversity, not from mixing tiers
  within one family.

Several of these results are preprints and are cited as research, not settled
fact. The Workflow tool's own guidance also prefers cheap inline scouting in the
main session before a fan-out.

## Decision

1. **Drop Round 2 (peer-rank).** The chair reads every schema-validated Round 1
   output in shuffled order, with persona labels kept so the Rationale and Panel
   Dissent blocks can attribute.
2. **Run the selector inline.** The main session picks the lineup by rule, before
   the Workflow call. The Security force-floor is a deterministic keyword or path
   match. The lineup is shown to the user before any agent runs, then passed into
   the Workflow via `args`.
3. **Conditional seats are 0-2** (3-5 seats total). `--seats` still swaps and never
   adds, extra names beyond 2 are dropped and reported to the user, and Security remains
   non-removable: when the floor fires and `--seats` does not name it, Security
   displaces the last named seat.
4. **One tier for seats, a stronger chair.** All seats run on sonnet; the chair
   runs opus at high effort. The per-seat model-tier column is dropped. This is a
   maintainer choice and departs from the Workflow guidance to omit `model`.
5. **Remove the sub-skill invocation section.** It could not work:
   `disable-model-invocation: true` stops other skills and model turns invoking
   council, and the Workflow tool is unavailable inside subagents.
6. **Fallback when the Workflow tool is unavailable.** Run the same seat briefs as
   parallel Agent-tool calls and the chair as one more; if neither tool is
   available, stop and say so rather than simulating the panel in one context.

## Amends ADR 0036

[ADR 0036](./0036-council-skill-drives-workflow-tool.md)'s three-round structure
becomes two. Its amendment from PR #531, which stripped reasoning traces and
labels in Round 2, is moot for council: with no second round there is nothing to
isolate, and the seat `schema` returns only the validated object. ADR 0036's
decision stands: skills may drive the Workflow tool, under its authoring rules 1-4.
Its sentence that `repo-audit`'s Round 2 carries the same tightening is untouched
here.

## Out of scope

`repo-audit` keeps its own Round 2 until its separate change (since done; see Amendments).

## Amendments

### 2026-10-12 — `repo-audit`: Round 2 cross-review removed ([#600](https://github.com/dividedby/skills/pull/600))

**Context.** `repo-audit` Stage 2 mirrored `/council`: a blind Round 1 sweep (5
seats), a Round 2 anonymized cross-review and dedup (5 agents), then a synthesis.
ADR 0036's #531 amendment extended dual (label and trace) isolation to that round.
A run cost 11 agents.

**Decision.** Round 2 is removed from `repo-audit` for the reason it was dropped
from `/council`: peer rationales induce conformity and debate does not beat voting
at equal compute. The single synthesis agent now (a) verifies each finding at its
cited path and drops those it cannot confirm, listing each drop with a reason; (b)
merges duplicates by root cause; (c) confirms altitude; and (d) adds no new
findings. Seats run on one tier with schema-validated output, and a run uses at
most 6 agents.

**Why verification beats cross-review here.** Audit findings are checkable claims
about files, so grounding them against the repo is a stronger filter than peer
agreement, and it avoids conformity bias.

**Consequences.** The trace-stripping prose in `repo-audit` is deleted, because
schema output carries no trace. The `repo-audit` sentence in ADR 0036's #531
amendment is superseded for `repo-audit`. Round 1 blind isolation is retained. ADR
0036's authoring rules still apply, with rule 3 (schema at the output boundary)
now covering seats as well as synthesis.

## Consequences

- A run costs about 4-6 agents instead of about 12.
- The Falsifier FP-exclusion list is unchanged and remains canonical for the
  published plugin.
- The cross-seat ranking signal is lost. This is accepted given the evidence above.
- Reinstating peer-rank would need a new decision.
