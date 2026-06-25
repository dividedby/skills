# Skill Authoring

Committed, loop-readable lore for authoring skills in this repo. This is the
internal craft doc — not invokable as a skill, not a code index. Remote loops
that clone the repo can read it directly from `docs/agents/`.

Scope decided in [ADR 0028](../adr/0028-skill-authoring-lore-lives-in-docs-agents-not-a-code-indexer.md).

---

## Composition-Pattern Catalog

When a skill is an **orchestration wrapper**, it calls sub-skills to avoid
duplicating their vocabulary. The table below records which wrappers call which
sub-skills, and when that composition fires.

### `software-design` (orchestrator)

**File:** `skills/engineering/software-design/SKILL.md`

The canonical wrapper for multi-module design sessions. Composes:

- **`/codebase-design`** (step 4) — deep-module/seam framework, deletion test,
  decomposition heuristics, adapter strategy, testability principles. All
  module-vocabulary doctrine lives here; `software-design` does not duplicate it.
- **`/domain-modeling`** (step 5) — ubiquitous-language grounding. Confirms or
  corrects candidate module/interface names against `CONTEXT.md`; flags new terms
  for `/grill-with-docs` extraction.
- **`/grill-with-docs`** (deferred surface) — owns `CONTEXT.md` and `docs/adr/`.
  When the design session surfaces a new domain term or an ADR-worthy trade-off,
  `software-design` surfaces it and defers the write to `/grill-with-docs`.
- **`/frontend-design`** (routing stamp) — `software-design` stamps frontend-
  flavored issues with a routing block and hands off; it does not design components.

**Trigger for composition:** the backlog plausibly spans two or more modules and
module/seam choices are still implicit.

### `grill-with-docs` (thin wrapper)

**File:** `~/.claude/skills/grill-with-docs/SKILL.md` (globally installed; see [`installed-skills.md`](./installed-skills.md))

A two-line wrapper: runs `/grilling` with the `/domain-modeling` skill in scope.

- **`/grilling`** — relentless interview loop, one question at a time, until
  shared understanding is reached. The raw questioning discipline.
- **`/domain-modeling`** — writes down what crystallises: pins terms into
  `CONTEXT.md`, records hard decisions as ADRs in `docs/adr/`.

**Trigger for composition:** any time domain vocabulary needs to be established or
an architectural decision needs to be recorded. `software-design` defers to this
pair when new terms or trade-offs surface mid-session.

### `FIREWALL.md` (copy-in pattern)

**File:** `skills/engineering/autonomous-loop/FIREWALL.md`

Not a skill and not an orchestrator — a generic context-hygiene discipline doc.
Copy a reference into any multi-item skill (loop or loopless) rather than
authoring a new sub-agent runtime: point to FIREWALL.md for the per-item
sub-agent shape, budget-checkpoint placement, and compaction mechanics.

**Trigger for composition:** a skill's workflow runs over a backlog or processes
multiple items in sequence. Reference the FIREWALL.md discipline in the skill's
multi-item section rather than re-deriving it inline.

### `autonomous-loop`

**File:** `skills/engineering/autonomous-loop/SKILL.md`

Methodology skill for running unattended agent loops safely. Composes into
skill-authoring when a skill is designed to run AFK or scheduled — prescribe
the five autonomous-loop elements (stop condition, proposal gate, budget check,
HITL hardening, input durability) rather than re-deriving them inline.

**Trigger for composition:** a skill's design session produces a loop that will
run unattended. Point to `/autonomous-loop` for the discipline; do not author
a new runtime.

---

## Editorial-Judgement Log

Worked examples of the "prescribe at the principle level" discipline from
[ADR 0002](../adr/0002-design-skills-prescribe-at-principle-level.md).
Source: ADR 0002 + issues #11 and #12.

### What the rule says

Skills prescribe **principles**, not stack-specific idioms. Code examples inside
a skill are **illustrative sketches** — they show the shape of a principle, not
the rule itself. The same principle ("encode order in the types") plays out
differently across stacks; hardening one language's idiom into the prescription
narrows the skill's reach or misleads readers on other stacks.

### Worked example: issue #12 — temporal coupling in testability.md

**The proposed change:** the original text for the temporal-coupling anti-pattern
read: *"Each operation should be callable independently, or the required order
should be enforced by the type system."* Issue #12 proposed replacing this with a
full TypeScript before/after pair (a `class Fulfillment` / `function reserve()`
typestate pattern) to make the remedy concrete.

**The judgment call:** the fix was rejected in its proposed form. The resolution
sharpened the *prose* to name the shape — "`reserve()` returns a token
`dispatch()` requires as input, so the wrong order won't compile" — without
adding a language-specific code block.

**Why:** the anti-patterns section is deliberately terse (short diagnosis +
one-line remedy per item). Every other anti-pattern in that section has a
self-evident plain-English remedy. Adding a full TS pair to *this* item would:

1. Inflate one anti-pattern out of proportion to the other three.
2. Prescribe TypeScript's typestate idiom as *the* remedy, when the principle
   is stack-agnostic ("encode order structurally, not at runtime").

The repair: name the mechanism in prose, not code.

**Decision heuristic derived:** before adding a code example to a skill, ask
*"does prose fail here?"* If the remedy is a technique reference (not a
self-evident instruction), sharpen the prose to name the shape. Resort to code
only when prose genuinely cannot convey the shape — and then note in the ADR why
prose failed.

### Worked example: issue #11 — shadow scale in design-tokens.md

**The proposed change:** every token taxonomy in `design-tokens.md` (spacing,
motion, color) shipped concrete starting values. The shadow scale was the outlier:
it named levels (`--shadow-sm`, `--shadow-md`, …) but gave no CSS values. Issue
#11 proposed adding them for consistency.

**The judgment call:** the change was accepted. The surrounding section already
shipped example values for all sibling taxonomies; the shadow scale was a gap
in *section density*, not an overshoot.

**Why this differs from #12:** adding values here restored symmetry to an
*established pattern within the same section* — it did not elevate one item
above its siblings. When the surrounding section already contains code (or
concrete values), adding a missing peer example is correct; it is not prescribing
a new literal rule.

**Decision heuristic derived (ADR 0002 consequence):** *match local section
density.* If sibling items already ship code, adding one to a missing sibling
restores symmetry. If the section is deliberately terse, adding code to one
item signals that the snippet IS the rule, when it isn't.

### Summary: the two-question test before adding a code example

1. **Does prose fail?** If the prose can name the shape clearly, prefer prose.
2. **Does the surrounding section already contain code?** If yes, a missing peer
   example restores symmetry. If no, adding code elevates this item above its
   siblings without a reason.

If both answers are "yes" (prose fails AND the section already has examples),
adding code is correct. If neither is true, add code only with an explicit
rationale recorded here.

---

## Deferred Sections

Per ADR 0028, these were seeded but deliberately not written:

- **Rejection runbook** — rationale for why a skill was rejected or moved to
  `.out-of-scope/`. Deferred: `.out-of-scope/` already partially serves this.
  Revisit when rejection rationales get re-argued despite `.out-of-scope/` being
  present.
- **Antipattern collection** — known skill-authoring antipatterns. Deferred for
  the same reason. File against this doc when an antipattern recurs.
