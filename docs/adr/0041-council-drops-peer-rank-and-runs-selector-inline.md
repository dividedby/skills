# Council drops its peer-rank round and runs the selector inline

> **Status: Accepted** — maintainer decision (2026-10-12). **Amends [ADR 0036](./0036-council-skill-drives-workflow-tool.md).**

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
   adds, extra names beyond 2 are dropped and logged, and Security remains
   non-removable.
4. **One tier for seats, a stronger chair.** All seats run on sonnet; the chair
   runs opus at high effort. The per-seat model-tier column is dropped. This is a
   maintainer choice and departs from the Workflow guidance to omit `model`.
5. **Remove the sub-skill invocation section.** It could not work:
   `disable-model-invocation: true` stops other skills and model turns invoking
   council, and the Workflow tool is unavailable inside subagents.

## Amends ADR 0036

[ADR 0036](./0036-council-skill-drives-workflow-tool.md)'s three-round structure
becomes two. Its amendment from PR #531, which stripped reasoning traces and
labels in Round 2, is moot for council: with no second round there is nothing to
isolate, and the seat `schema` returns only the validated object. ADR 0036's
decision stands: skills may drive the Workflow tool, under its authoring rules 1-4.
Its sentence that `repo-audit`'s Round 2 carries the same tightening is untouched
here.

## Out of scope

`repo-audit` keeps its own Round 2 until its separate change.

## Amendments

None yet. `repo-audit`'s removal of its own Round 2 will be recorded here as a
dated amendment, with its PR link, rather than as a new ADR.

## Consequences

- A run costs about 4-6 agents instead of about 12.
- The Falsifier FP-exclusion list is unchanged and remains canonical for the
  published plugin.
- The cross-seat ranking signal is lost. This is accepted given the evidence above.
- Reinstating peer-rank would need a new decision.
