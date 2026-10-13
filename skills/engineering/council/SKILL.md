---
name: council
disable-model-invocation: true
description: Convene a blind multi-persona panel on a non-trivial design decision and return a synthesis plus the dissent the chair did not adopt.
---

# Council

`/council` evaluates a decision through personas with distinct lenses, blind and
in parallel, then a chair synthesizes it with a "panel dissent" block preserving
what it did not adopt. It wraps the built-in `Workflow` tool: persona logic
lives in seat prompts; this skill contributes the selector, roster, round
structure, and dissent contract.

Defers:
- `Workflow` tool (built-in) — blind seat isolation and schema enforcement.
- ADR 0036 and ADR 0041 (`docs/adr/`) — design rationale.
- `/code-review` (upstream) — line-level defects.

## When to Run

Design-level decisions where one perspective is likely to miss an objection: an
architecture trade-off with real alternatives; hard-to-reverse content or UX
direction; a hypothesis that resists the obvious fix; a PR's design-level blind
spot; any task the requester has already convinced themselves about. Not for
line-level defects (use `/code-review`) or trivial changes.

## Roster

Eight personas; all seats run on sonnet, the chair on opus at high effort.

### Core seats (always active, 3)

| Persona | Lens |
|---|---|
| **Falsifier** | Find the claim that breaks the proposal. One focused objection — no filler. |
| **Minimalist** | What can be deleted, deferred, or simplified without losing the value? Shorter is the default. |
| **Pragmatist** | Given the real constraints (team, timeline, debt), what actually ships and holds? |

### Conditional seats (5 available, 0-2 active)

| Persona | Activate when… |
|---|---|
| **Operator** | The proposal runs in production — ops burden, failure modes, observability |
| **Convention Keeper** | The codebase has strong conventions and the proposal may violate them |
| **Security** | **Hard-floor:** any signal of auth, payments, secrets, migrations, or trust boundary. Force-seated by the selector regardless of `--seats`. |
| **Performance** | The hot path, query plan, or payload size is on the table |
| **Frontend-UX-a11y** | The output is a visible surface, interaction, or accessibility-affecting change |

**Panel size:** 3 core + 0-2 conditional = 3-5 seats; a conditional is seated
only on a real signal, and Security counts against the 2.

### Falsifier FP-exclusion list

The Falsifier hunts for the objection that breaks the proposal — not for
noise dressed up as an objection. It does not report:

- Pre-existing issues — already present before this diff, not introduced by it.
- Issues a linter, typechecker, or compiler would catch on its own (CI covers these).
- Issues explicitly silenced in the code (e.g. a lint-ignore comment) — deliberately suppressed, not missed.
- Changes in functionality that look intentional and are directly related to the broader change.
- Real issues, but on lines the diff didn't touch.
- General code-quality gripes (test coverage, docs, style) absent a documented standard (CLAUDE.md, ADR, or repo convention) that the diff violates.

This list is canonical for the published plugin. A mirror lives in the maintainer's `~/.claude/branching-flow.md` review gate (not in this repo) — kept in sync by hand.

## Step 0 — Selector (inline, before the Workflow)

The main session picks the lineup by rule; no agent is spawned.
1. Read the task text and signals (paths, diff headers, labels, keywords).
2. **Security force-floor:** seat Security on any signal of auth, payments,
   secrets, migrations, or trust boundary — a keyword or path match, not a
   judgment call, regardless of `--seats`.
3. Seat other conditionals only on a matching signal; zero is valid.
4. `--seats A,B` replaces the conditional choices (swap, never add). If more
   than 2 are named, keep the first 2 and report the dropped names. If the
   Security floor fires and is not named, it displaces the last named seat
   (reported); Security is never removable.
5. Show the lineup (one-line rationale per seat, skipped seats with reason) to
   the user before the Workflow call, then proceed without pausing; pass it in
   via `args`.

```
Lineup for "introduce JWT auth middleware":
  ✓ Falsifier, Minimalist, Pragmatist (core) · Security (auth keyword, force-floor)
  ✓ Convention Keeper — strong middleware conventions at risk
  ✗ Operator, Performance, Frontend-UX-a11y — no matching signal
```

## Rounds

**Round 1 — Blind parallel evaluation.** Each active seat runs in one
`parallel()`. Seats do **not** see each other's output; each receives the same
task text and its own persona prompt, nothing else. The seat `schema` is five
fields:

- `seat`
- `verdict` — approve / approve-with-changes / reject
- `core finding` — the single most important thing this lens sees
- `evidence` — specific, not general principles
- `recommendation` — what to do, not just what's wrong

**Final round — Chair synthesis.** A dedicated Chair (opus, effort high) reads
every seat's validated output in shuffled order (position-bias mitigation),
persona labels kept so Rationale and Panel Dissent can attribute. Chair brief:
treat each seat output as unvetted; do not average — resolve the key trade-off;
name what you rejected.

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

## Invocation

```
/council "Should we move the billing module to a separate service now or wait
         until we hit 10k active subscriptions?"
/council --seats "Operator,Performance" "What is the right caching strategy
         for the product catalog?"
```

`--seats` swaps in up to 2 conditional seats; core seats stay, Security is never removable.

## Illustrative Workflow Sketch

```
// illustrative only — not a runnable script (ADR 0002)
// args = { task, seats: [{ persona, lens }] }  — the Step 0 lineup
const seats = await parallel(args.seats.map(s => () =>
  agent(seatPrompt(s, args.task),
    { label: s.persona, phase: "evaluate", schema: SeatSchema, model: "sonnet" })
));
log(`council: ${seats.length} seats`);
return agent(chairPrompt(shuffle(seats)),   // shuffle: plain script code
  { label: "chair", phase: "synthesize", schema: CouncilOutputSchema,
    model: "opus", effort: "high" });
```

- Seats are blind with identical input; outputs are schema-validated objects.
  The Chair is a dedicated agent reading shuffled but labelled outputs.
- `CouncilOutputSchema` enforces the four output blocks, so a partial response
  is a Workflow error (ADR 0036 rule 3).

## Availability and fallback

`disable-model-invocation: true` means no other skill or model turn can invoke
council, and Workflow is unavailable inside subagents, so run it from the main
session. Without the Workflow tool, run the same briefs as parallel Agent-tool
calls in one message (seats on sonnet), then the chair as one more Agent call
(opus); with no schema enforcement there, check for the four output headings
and re-ask the chair once if any is missing. With neither tool, stop and say
so; do not simulate the panel in one pass.

## Checklist Per Council Run

- [ ] Lineup shown before any agents run
- [ ] Security floor applied
- [ ] Seats blind (no cross-seat input)
- [ ] Chair read every seat's output
- [ ] Output has all four blocks, including a non-empty Panel Dissent
