---
name: write-well
disable-model-invocation: true
description: >
  Draft and de-slop English prose to a defensible core and clean output. Two
  entry points: draft and improve.
---

# Write Well

Draft and de-slop English prose. Two entry points: **draft** builds from a
blank page, **improve** polishes text you bring.

The de-slop rules in this skill govern prose it *produces*. They do not govern
this instruction doc.

**Mode** is one parameter, picked once: `article` (narrative arc,
evidence-bound), `readme` (scannable, action-first), or `general` (default,
minimal structural opinion). Mode sets the target for the structure step. The
de-slop layer and the gates run the same in every mode.

## Grounding and structure

Both entry points rest on two principles.

**Grounding.** Every concept must be **grounded** before a later beat leans on
it: either **reader-brings** (a prerequisite the reader already holds) or
**must-define** (this piece introduces it). Set that line with the user before
drafting. An ungrounded concept the next move needs is a structural blocker,
not a style nit. Ground it or restructure.

**Structure.** Weight asymmetry is deliberate. Decide which section deserves
40% and which 5% before writing. Pick an arc and state it: `problem → solution
→ evidence`, `story → principle → application`, or `counterintuitive claim →
proof → implications`. Skim test: a heading-only read still conveys the
argument.

## Entry point: draft

1. **Core-finding.** Dig until the core is one defensible sentence. Protocol:
   [`references/core-finding.md`](references/core-finding.md).
   **Done when:** one sentence states the core and the stress-test verdict is
   *holds*.

2. **Grounding and structure.** Set the reader-brings vs must-define line. Name
   the arc. Draft a weight map (section → share of total).
   **Done when:** line set, arc named, weight map drafted, skim test passes.

3. **Draft.** Write the full piece in the chosen mode, following the weight
   map. Ground every concept before it appears.
   **Done when:** full draft exists and no concept arrives ungrounded.

4. **De-slop.** Run the layer. Protocol:
   [`references/de-slop.md`](references/de-slop.md).
   **Done when:** the De-slop gate is green.

5. **Gates.**
   **Done when:** every red-line gate below is green.

## Entry point: improve

Bring your own text. Skip core-finding.

1. **Structure-check.** Identify the arc. Audit section weight against actual
   word counts. Run the skim test.
   **Done when:** arc named, over- and under-weighted sections adjusted.

2. **Density.** Apply the sentence-load test from
   [`references/de-slop.md`](references/de-slop.md) to every sentence.
   **Done when:** no scaffold or ornament sentence remains.

3. **De-slop.** Run the layer. Protocol:
   [`references/de-slop.md`](references/de-slop.md).
   **Done when:** the De-slop gate is green.

4. **Gates.**
   **Done when:** every red-line gate below except the Core gate is green.

## Red-line gates

Pass or fail. A failing gate blocks delivery.

- **Core gate** *(draft only)*. The core is one defensible sentence. If it
  takes two, core-finding isn't done; return to core-finding.
- **Density gate.** Every sentence carries work. Remove the sentence; if the
  argument is unchanged, cut it.
- **Burstiness gate.** Sentence length varies. Uniform-length sentences read as
  machine output.
- **De-slop gate.** All de-slop passes ran; the output carries no em-dashes or
  en-dashes; AI-trace tells were judged in clusters, not isolation; the
  typographic-tell pass ran.
- **Evidence gate.** No invented facts. Vague-source claims ("studies show",
  "teams report") are flagged as proof gaps and sourced or cut, never laundered
  into assertions.

## References

- [`references/core-finding.md`](references/core-finding.md): the draft core
  engine — four shovels, the attack, the stress-test gate.
- [`references/de-slop.md`](references/de-slop.md): the de-slop layer —
  sentence-load density, burstiness, AI-trace passes, typographic tells,
  evidence-bound mode.

## Attribution

Core-finding, the structural weight-and-arc framework, and the gate spine are
adapted from **d-wwei/great-writer** (MIT). The grounding principle
(reader-brings vs must-define) is adapted from mattpocock's writing-shape.
Sentence-load density and evidence-bound mode are adapted from ehmo/slopbeth.
The typographic-tell list is adapted from weijt606/anti-vibe-writing. The
AI-trace audit is adapted from blader/humanizer.

> d-wwei/great-writer is MIT-licensed. This skill is an independent synthesis,
> not a derived work or a soft-depend wrapper. See ADR 0035.
