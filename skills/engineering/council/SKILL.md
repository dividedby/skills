---
name: council
description: >
  Convene a blind, diverse multi-persona panel that returns a synthesized
  second opinion plus the dissent the chair did not adopt. Drives the
  built-in Workflow tool (parallel seats → peer-rank → chair synthesis).
  Use on any non-trivial decision — design trade-offs, architecture choices,
  PR review, debugging hypotheses, content direction.
disable-model-invocation: true
---

# Council

`/council` convenes a panel of personas — each with a distinct evaluative
lens — runs them in three structured rounds via the built-in `Workflow` tool,
and returns a synthesis plus a "panel dissent" block preserving what the chair
did not adopt. The goal is adversarial diversity: surface the objection the
requester did not think to make, then decide with it in view.

It is an **orchestration wrapper** over the Workflow tool's `parallel()` /
`pipeline()` / `agent()` primitives. The personas' evaluative logic lives in
their seat prompts; this skill contributes the selector, the roster, the round
structure, and the dissent contract.

---

## When to Run

Any decision where a single perspective is likely to miss an important
objection:

- Architecture or design trade-off with real alternatives
- PR review where the author suspects a blind spot
- Debugging a hypothesis that keeps resisting the obvious fix
- Content or UX direction that will be hard to reverse
- Any task the requester has already convinced themselves about

Not every task needs a council. A one-line config change does not. Apply
judgment — or let the selector (Step 0) make the call.

---

> **Temporary — revert on/after 2026-07-07 (Fable 5 sunset).** The chair and the opus-tier seats below run on **Fable 5** for a trial. Revert: every `fable` in this file → `opus`.

## Roster

Eight personas, divided into two tiers. **Seats vary by persona and model
tier** — fable for the highest-leverage lenses, sonnet for speed-optimized
roles.

### Core seats (always active, 3)

| Persona | Model tier | Lens |
|---|---|---|
| **Falsifier** | fable | Find the claim that breaks the proposal. One focused objection per round — no filler. |
| **Minimalist** | sonnet | What can be deleted, deferred, or simplified without losing the value? Shorter is the default. |
| **Pragmatist** | fable | Given the real constraints (team, timeline, debt), what actually ships and holds? |

### Conditional seats (5 available, default 2 active)

| Persona | Model tier | Activate when… |
|---|---|---|
| **Operator** | sonnet | The proposal runs in production — ops burden, failure modes, observability |
| **Convention Keeper** | sonnet | The codebase has strong conventions and the proposal may violate them |
| **Security** | fable | **Hard-floor:** any signal of auth, payments, secrets, migrations, or trust boundary. Force-seated by the selector regardless of `--seats`. |
| **Performance** | sonnet | The hot path, query plan, or payload size is on the table |
| **Frontend-UX-a11y** | sonnet | The output is a visible surface, interaction, or accessibility-affecting change |

**Default panel: 5 seats** — the 3 core seats plus 2 conditional seats chosen
by the selector. The `--seats` override can substitute different conditional
seats, but **does not add seats above 5** (swap-not-add keeps cost flat).
Security is force-seated on any auth/payments/secrets/migrations signal even if
`--seats` does not name it.

### Falsifier FP-exclusion list

The Falsifier hunts for the objection that breaks the proposal — not for
noise dressed up as an objection. It does not report:

- Pre-existing issues — already present before this diff, not introduced by it.
- Issues a linter, typechecker, or compiler would catch on its own (CI covers these).
- Issues explicitly silenced in the code (e.g. a lint-ignore comment) — deliberately suppressed, not missed.
- Changes in functionality that look intentional and are directly related to the broader change.
- Real issues, but on lines the diff didn't touch.
- General code-quality gripes (test coverage, docs, style) absent a documented standard (CLAUDE.md, ADR, or repo convention) that the diff violates.

Mirrored verbatim in `flow-pr`'s step-4 review gate (`skills/engineering/flow-pr/SKILL.md`) — keep the two lists in sync.

---

## Step 0 — Selector

Before convening the panel, run a single cheap classifier call (haiku or
sonnet-level) that reads:

- The task text or question
- Target signals (file paths, PR diff headers, issue labels, keywords)

The classifier **outputs, for every candidate seat**, whether it is active and
a one-line rationale. It also resolves any `--seats` override against the
force-floor rule (Security can never be removed by an override). Log the final
lineup and rationale before Round 1 begins.

Illustrative selector output:

```
Panel lineup for: "introduce JWT auth middleware"
  ✓ Falsifier (core / fable)       — always on
  ✓ Minimalist (core / sonnet)     — always on
  ✓ Pragmatist (core / fable)      — always on
  ✓ Security (force-floor / fable) — auth keyword detected
  ✓ Convention Keeper (conditional / sonnet) — codebase signal: strong middleware conventions
  ✗ Operator     — no ops-burden signal
  ✗ Performance  — no hot-path signal
  ✗ Frontend-UX-a11y — no visible-surface signal
```

---

## Three Rounds

### Round 1 — Blind parallel evaluation

Each active seat runs independently via `parallel()`. Seats do **not** see
each other's output. Every seat receives the same task text and its own
persona prompt; nothing else.

Each seat returns a structured response:

```
seat: <persona name>
verdict: <one of: approve / approve-with-changes / reject>
core finding: <the single most important thing this lens sees>
evidence: <specific, concrete — not general principles>
recommendation: <what to do, not just what's wrong>
```

### Round 2 — Anonymized peer-rank

Seat responses are anonymized (persona labels stripped) and redistributed.
Each seat reads the full set and:

1. Ranks the three strongest arguments (not its own)
2. Identifies one argument that is overclaiming or underweighted
3. Surfacing any new consideration the first round missed

This round does not produce a verdict — it produces a ranked evidence map
the chair uses in Round 3.

### Round 3 — Chair synthesis

A dedicated **Chair** agent (fable, higher effort) reads:

- All Round 1 responses (de-anonymized)
- The Round 2 ranked evidence map

The Chair produces the final output.

---

## Output Contract

Every `/council` run produces exactly this structure:

```
## Synthesis

<2–4 sentences: the decision or recommendation, incorporating the strongest
panel arguments. Names the key trade-off that was resolved and how.>

## Rationale

<Bullet list: each panel argument that shaped the synthesis, attributed to the
persona. Evidence-grounded — no generic principles.>

## Panel Dissent

<The strongest argument(s) the chair did not adopt, attributed to persona, with
the chair's explicit response to each. Required even when the synthesis is
unanimous — "no dissent" must be earned, not assumed.>

## Confidence

<high / medium / low, with one sentence on what would change the rating.>
```

The dissent block is **non-optional**. A synthesis with no dissent block is an
incomplete run.

---

## Invocation

### Standalone

```
/council "Should we move the billing module to a separate service now or wait
         until we hit 10k active subscriptions?"
```

With seat override (swap two conditional seats for the defaults):

```
/council --seats "Operator,Performance" "What is the right caching strategy
         for the product catalog?"
```

`--seats` names the conditional seats to activate. The 3 core seats are always
present. `--seats` overrides the selector's conditional choices but cannot
remove Security when the force-floor fires.

### As a sub-skill

Any skill can invoke `/council` before a hard-to-reverse decision:

```
Before committing to the module split, invoke /council with the proposed seam
and the two strongest objections surfaced in Step 3. Use its synthesis to
resolve the open question before writing to disk.
```

The invoking skill hands off the task text and any relevant context; `/council`
returns its structured output; the invoking skill incorporates the synthesis.

---

## Illustrative Workflow Sketch

The sketch below shows the *shape* of a Workflow-tool execution, not a literal
script. The actual prompts, schema, and effort settings are seat-specific and
tuned per run; this is a sketch of the orchestration pattern.

```
// ponytail: illustrative only — not a runnable literal script (ADR 0002)

const taskText = userInput;
const lineup   = await agent("selector", { model: "haiku", input: taskText });

// Round 1: each active seat runs blind in parallel
const round1 = await parallel(
  lineup.activeSeats.map(seat =>
    agent(seat.persona, { model: seat.model, effort: seat.effort, input: taskText })
  )
);

// Round 2: anonymized peer-rank
const anonymized = stripPersonaLabels(round1);
const round2 = await parallel(
  lineup.activeSeats.map(seat =>
    agent(seat.persona + "-rank", { model: seat.model, input: { anonymized, myResponse: round1[seat] } })
  )
);

// Round 3: chair synthesis
const synthesis = await agent("chair", {
  model:  "fable",
  effort: "high",
  input:  { round1, evidenceMap: round2 },
  schema: CouncilOutputSchema,   // enforces the four-block output contract
});

return synthesis;
```

Key orchestration properties:
- Round 1 isolation is strict: no seat sees another's output during Round 1.
- Round 2 is peer-rank, not re-evaluation: seats rank arguments, not re-state verdicts.
- The Chair is a dedicated agent, not the last seat to run — it reads all output
  with the synthesis responsibility explicit in its prompt.
- `CouncilOutputSchema` enforces the four-block output contract (Synthesis /
  Rationale / Panel Dissent / Confidence) at the schema level so a partial
  response is a Workflow error, not a silently incomplete synthesis.

---

## Checklist Per Council Run

```
[ ] Step 0 selector ran; lineup and per-seat rationale logged before Round 1
[ ] Security hard-floor checked (force-seated on auth/payments/secrets/migrations)
[ ] --seats override applied (swap-not-add; Security floor respected)
[ ] Round 1: all active seats ran blind (no cross-seat visibility)
[ ] Round 2: responses anonymized before redistribution
[ ] Round 3: Chair read full de-anonymized Round 1 + Round 2 evidence map
[ ] Output carries all four blocks: Synthesis / Rationale / Panel Dissent / Confidence
[ ] Panel Dissent block is non-empty (or explicitly earned "no dissent" with chair response)
```
