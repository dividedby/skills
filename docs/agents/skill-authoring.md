# Skill Authoring

Committed lore for authoring skills in this repo. This is the internal craft
doc — not invokable as a skill, not a code index.

Scope decided in [ADR 0028](../adr/0028-skill-authoring-lore-lives-in-docs-agents-not-a-code-indexer.md).

---

## Composition-Pattern Catalog

When a skill is an **orchestration wrapper**, it calls sub-skills to avoid
duplicating their vocabulary. The table below records which wrappers call which
sub-skills, and when that composition fires.

### `grill-with-docs` (upstream, soft-dependency)

**File:** `~/.claude/skills/grill-with-docs/SKILL.md` (globally installed)

A relentless interview loop, one question at a time, until shared understanding
is reached — and it writes down what crystallises: pins terms into `CONTEXT.md`
and records hard decisions as ADRs in `docs/adr/`.

**Trigger for composition:** any time domain vocabulary needs to be established or
an architectural decision needs to be recorded.

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

_Note: the `software-design` skill this example cites has been retired ([ADR 0040](../adr/0040-retire-unused-catalog-skills-and-fold-flow-pr-into-branching-flow.md)); the example is kept as editorial history._

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

_Note: the `frontend-design` skill this example cites has been retired ([ADR 0040](../adr/0040-retire-unused-catalog-skills-and-fold-flow-pr-into-branching-flow.md)); the example is kept as editorial history._

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
