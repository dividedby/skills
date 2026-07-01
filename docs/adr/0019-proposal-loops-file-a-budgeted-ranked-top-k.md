# Proposal loops file a budgeted ranked top-k, not one issue per run/channel

> **Amended 2026-06-30.** Per-run cap **2 → 1** for both `MAX_PROPOSALS`
> (`harness/cli.py`, reaching arch-review estate-wide) and the
> apply-agent-research gate `budget` (`proposal_gate.MAX_BUDGET`). Each
> scheduled run now files at most its single best proposal, or nothing.
> **Rationale:** in practice the 2-ceiling behaved as a target — loops filed 2
> nearly every run, and the second was consistently marginal, reading as
> tracker noise rather than signal. Reverting to a one-issue cap restores the
> pre-ADR-0019 discipline: the run files THE single best finding that clears
> the bar, or it files nothing. The ceiling-not-target discipline is preserved
> at k=1: a typical run still files 0–1, and silence is preferred over filler.
> Cadence is unchanged (3×/week Mon/Wed/Sat for `improve-codebase-architecture`
> and `apply-agent-research`; `staleness-review` monthly) — `staleness-review`
> already files a single ranked report and is unaffected by this amendment.
> Caps stay mechanical (in-code) and reach every consumer via the
> fetched-fresh harness/skill
> ([ADR 0014](0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md));
> no tag move is needed. This supersedes only the cap value set below; the
> cadence change from the 2026-06-20 amendment stands.

> **Amended 2026-06-20.** Two parameters change together now that the
> `claude -p` SDK credit — the cost constraint this ADR's "Why" rested on (the
> weekly cadence set by the 2026-06-08 cost-rebalance) — has been walked back by
> Anthropic. **(1) Per-run cap 5 → 2** for the budgeted loops: `MAX_PROPOSALS`
> (`harness/cli.py`, reaching arch-review estate-wide) and the
> apply-agent-research gate `budget` (`proposal_gate.MAX_BUDGET`). Caps stay
> mechanical and propagate to every consumer via the fetched-fresh harness/skill
> ([ADR 0014](0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)).
> **(2) Cadence weekly → 3×/week** (Mon/Wed/Sat) for `improve-codebase-architecture`
> and `apply-agent-research`, by expanding the cron day-of-week field and
> preserving each repo's hash-staggered minute/hour (agent-research ADR 0022);
> `staleness-review` is unchanged (monthly, one report). This adopts the pairing
> the "Rejected alternatives" below dismissed as *"keep ≤1 and raise cadence
> instead"* — but only partially: cadence rises **and** the per-run ceiling stays
> above 1 (=2), so findings discovered together are not re-serialized one-per-run.
> The "more runs cost more" objection is void without the credit. The
> ceiling-not-target discipline is preserved (typical run still 0–2); the only
> shift is that a maximal week per loop moves from 5 to 6 issues, spread across
> three smaller, fresher batches, cutting the wait for a serialized finding from a
> week to ~2 days. Out of scope: agent-research's producer-side scout budget
> (≤3) is a separate mechanism and is unchanged.

Every Claude-powered proposal loop moves from a one-issue cap to a **per-run
budget of 5** (lowered to **2** by the 2026-06-20 amendment above), enforced in
code, with an explicit ceiling-not-target discipline:

- **Harness loops** (`harness/cli.py publish` — architecture-review here and in
  every downstream repo): the `<output>` contract gains a `proposals[]` array
  with one `<body-N>` block per proposal; `publish` files at most
  `MAX_PROPOSALS = 5`, truncating (visibly, in the step summary) anything beyond.
- **apply-agent-research**: the per-channel one-proposal gate
  ([ADR 0011](0011-per-channel-proposal-caps.md), now **superseded**) becomes a
  single budgeted gate pass — `proposal_gate.decide(..., budget=5)` — run ONCE
  over the merged, ranked candidates from every enabled channel, with the union
  of every channel's spoken-for dedup keys. Channels keep their distinct labels
  and destinations; they share one budget.
- **staleness-review** is unchanged: it files one ranked *report* that already
  carries every finding — splitting it would add tracker noise, not signal.
- **agent-research's scout** adopts the same shape with a smaller budget (≤3):
  source proposals are reviewed by a human weekly and a larger batch would
  outpace triage.

**Why.** The one-cap regime discarded signal: a run that surfaced several
independently strong findings filed only the best and forgot the rest, and the
weekly cadence (post cost-rebalance, 2026-06-08) means a dropped finding waits a
week — or forever, if the next run ranks differently. A small budget keeps the
strong runner-ups without opening the floodgates.

**What is preserved — the bar, per proposal.** The prompts and skill docs all
state the same discipline: the budget is a **ceiling, not a target**. Each filed
proposal must independently clear the bar that would have made it *the* single
proposal under the old regime; a typical run files 0–2; filler erodes the
maintainer's trust in the loop faster than silence. The cap itself stays
mechanical (harness `MAX_PROPOSALS`, the gate's clamped `budget`), so prompt
drift cannot exceed it.

**Consequence.** A maximal week across all loops in one repo can now file more
issues than before (architecture-review ≤5 + apply-agent-research ≤5 + the
single staleness report). We accept this because the common case stays 0–2 per
loop, every issue still carries provenance labels and dedup keys, and the human
triage path (close / `wontfix`) remains the decider.

**Rejected alternatives.**

- *Keep ≤1 and raise cadence instead* — more runs cost more (each run re-reads
  the corpus/repo) and still serialize findings discovered together.
- *Unbounded "file everything worth filing"* — no mechanical backstop against a
  bad run spraying the tracker; the in-code cap is the safety property the
  propose-only posture rests on.
- *Per-channel budgets of 5 for apply-agent-research* — a maximal run could file
  15+ issues across channels; the shared budget bounds the whole run at the same
  5 as every other loop.
