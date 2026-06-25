# Evaluator gate

Detail for [SKILL.md](SKILL.md) element 6. **Illustrative sketches** (ADR 0002),
not a fixed procedure — adapt to the work in front of you.

When element 2's binary gate misfires — work subjective or under-specified enough
that it passes mechanically but the output is wrong quality — split the iteration
into a **generator pass** (produce the output) and a separate **evaluator pass**
(judge it), each with a clean context boundary between them.

## Generator / evaluator split

Separate producing from judging. The generator agent implements; the evaluator
agent reads the output cold (no shared context with the generator) and scores it
against a rubric. The separation matters: a single agent that generates and
immediately self-grades is prone to confirming its own assumptions. A cold
evaluator is structurally independent.

## Rubric design

Score across multiple dimensions that the work actually needs to succeed — not a
single overall rating. Each dimension should be independently scorable and map
to a real failure mode (e.g. correctness, completeness, tone, scope adherence).
A threshold per dimension surfaces *what* is weak, not just *whether* to retry.

## Calibration via examples

Anchor the rubric with a handful of worked examples before the loop runs — one
that should score high, one that should score low, one edge case. Rubric
language that seems clear often drifts in practice; examples pin the intended
interpretation and give the evaluator agent something to triangulate against.

## Sprint contracts

Before each generator pass, state explicitly what the unit of work commits to:
scope boundary, acceptance condition, and what the evaluator will check. This is
the evaluator-aware counterpart to element 5's brief-durability check — it
prevents the generator from producing output the rubric was never designed to
judge.

## Cost heuristics

The evaluator pass costs tokens. It earns them when: the output is hard to
verify mechanically (no deterministic gate), retries are cheap relative to a
wrong output landing, or the failure mode is subtle enough that a binary gate
misses it. It does not earn them when tests already catch the failure or the
work is narrow enough that the generator's own gate is reliable. Default to the
binary gate (element 2); reach for the evaluator split only when the binary gate
demonstrably misses quality failures.
