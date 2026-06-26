# `write-well` is built fresh — a scoped exception to the soft-depend-over-reinvention default

> **Status: proposed** — pending ratification via the PR that lands this file. Records a decision from a `/grill-with-docs` session (2026-06-25) triaging [#470](https://github.com/dividedby/skills/issues/470). Names a deliberate exception to [ADR 0024](./0024-lean-on-upstream-skills-soft-depend-over-reinvent.md) for one skill; it does **not** weaken 0024's default.

## Context

[ADR 0024](./0024-lean-on-upstream-skills-soft-depend-over-reinvent.md) sets the default: when Matt's upstream skill covers a capability, **delete + soft-depend** (a documented install-alongside expectation), not reinvent. [#470](https://github.com/dividedby/skills/issues/470) proposes a new `engineering/` skill, `write-well` — a lean, English-only prose **draft + de-slop** skill, rebuilt fresh from [`d-wwei/great-writer`](https://github.com/d-wwei/great-writer) (MIT) and folding in concepts from four other repos. Building a self-contained skill is, on its face, the reinvention 0024 biases against, so the exception must be stated.

The capability in question — a **fused** "find the core → structure → draft → de-slop" English writing engine — is spread across five disparate sources, none of which covers it alone:

- [`mattpocock/skills` → `writing-shape`](https://github.com/mattpocock/skills) — an *in-progress* Matt skill; narrative structure only. Contributes one concept (*grounding*).
- [`blader/humanizer`](https://github.com/blader/humanizer) (26k★, non-Matt) — de-slop taxonomy + voice; no narrative structure.
- [`ehmo/slopbeth`](https://github.com/ehmo/slopbeth), [`weijt606/anti-vibe-writing`](https://github.com/weijt606/anti-vibe-writing) (non-Matt) — density / evidence-bound / typographic-tell rules.
- [`d-wwei/great-writer`](https://github.com/d-wwei/great-writer) (MIT, Chinese-leaning, stale) — the only near-superset, but under-executed and not English-first.

A `/cba-searching` scan (2026-06-25) found **0 of ~12 similar installable skills cover the fused feature set**.

## Decision

Build `write-well` **fresh and self-contained**, as a one-off exception to ADR 0024, for these reasons:

1. **No single upstream covers the capability.** 0024's soft-depend default targets reinventing an upstream skill that already *covers* a capability. None here does — the value is the *synthesis* of narrative structure (F1) with de-slop/voice (F3), English-only: new differentiated value, not a reimplementation of any one upstream. (0024's own independent-value carve-out names *automation and convention* skills; the appeal here is to its spirit — keep differentiated work in-repo — not its letter.)
2. **Soft-depend's contract surface does not apply.** A soft-dependency under 0024 is a documented install-alongside expectation for an installable skill. The sources are a Chinese prompt repo, a 26k★ taxonomy, an in-progress Matt skill, and two third-party editors — not five composable Claude skills. "Install alongside all five" yields no coherent English skill.
3. **English-only + coherence require absorption, not composition.** The borrowed pieces are absorbed as principle-level rules ([ADR 0002](./0002-design-skills-prescribe-at-principle-level.md)), not vendored or wrapped. The skill reads as one coherent thing, not a meta-router over five incompatible sources.

**Constraints carried:**

- `write-well` is authored to the `writing-great-skills` standard (ADR 0024's authoring standard) and prescribes at the principle level ([ADR 0002](./0002-design-skills-prescribe-at-principle-level.md)) — borrowed rules are illustrative sketches, not literal checklists.
- The exception is **scoped to this one skill.** ADR 0024's delete-and-soft-depend default stands unchanged for every other capability — including a future Matt upstream that grows to cover fused prose writing, at which point this decision is revisited.

## Consequences

- [#470](https://github.com/dividedby/skills/issues/470) builds the skill per the agreed brief (lean core, two entry points, English-only); the deferred doc-it fold-in and changelog voice-pass remain its named follow-ups.
- `writing-shape` is **not** soft-depended on; its *grounding* concept is absorbed. If that later reads as overlap with a Matt skill, the supply-side audit ([ADR 0010](./0010-consumers-audit-local-skills-supply-side.md)) re-examines it against this ADR.
- No `CONTEXT.md` / `README.md` upstream-soft-dependency entry is added for `write-well` — it is a built skill, not a soft-dependency.
- `great-writer` is MIT; attribution (and credit for the borrowed concepts) is carried in the skill.
