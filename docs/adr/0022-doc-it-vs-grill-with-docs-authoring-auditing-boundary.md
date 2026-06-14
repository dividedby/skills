# doc-it and grill-with-docs have non-overlapping scopes: auditing vs authoring

Two skills touch documentation: `doc-it` generates and patches **reference
docs** (README, API docs, onboarding, CHANGELOG) and audits existing ADRs /
`CONTEXT.md` for staleness; `grill-with-docs` authors **new decisions and
terms** interactively. Without an explicit boundary, a maintainer could
invoke either for the wrong task, or a future skill edit could silently drag
one into the other's territory.

The boundary matters because the postures are opposite. `doc-it` improves
what exists — it applies changes directly to reference docs, and surfaces
drift in decision records as a list for a human to act on. `grill-with-docs`
produces new ADRs and new `CONTEXT.md` terms that didn't exist before.
Letting `doc-it` author new decisions would bypass the interactive interview
that `grill-with-docs` uses to validate them; letting `grill-with-docs`
patch reference prose would blur its scope. Either entanglement creates a
skill that is harder to invoke correctly and harder to reason about.

## Decision

`doc-it` and `grill-with-docs` divide documentation work on a single axis:

- **`doc-it` owns auditing and improvement.** It reads what exists (source
  code + existing docs), patches reference docs that are missing or stale,
  and reports ADR / `CONTEXT.md` drift findings without acting on them.
- **`grill-with-docs` owns new-decision authorship.** It conducts an
  interactive interview and produces new ADRs and new `CONTEXT.md` terms.

The seam is defined by **novelty**:

- If the work produces a fact that already exists in some form (a stale README
  section, a drifted API doc) and can be derived purely from local source —
  `doc-it`.
- If the work produces a fact that does not yet exist and requires a judgment
  call that should be validated with a human before committing — `grill-with-docs`.

When `doc-it` encounters a doc gap that requires a new architectural decision
(not just a missing factual description), it names the open question and stops
— it does not draft the decision. The maintainer invokes `grill-with-docs`
for that step.

## Consequences

- `doc-it` never authors new ADRs or new `CONTEXT.md` terms, regardless of
  what the scan reveals. If a gap warrants one, it is an explicit finding in
  the render output, not a created file.
- `grill-with-docs` does not patch reference docs or audit prose; its output
  is always a new decision artifact.
- The two skills are independently invokable and non-overlapping. A maintainer
  who wants both (e.g. patch the README *and* decide a new term) runs them in
  sequence, not as alternatives.
- Future skills that touch docs should self-locate relative to this axis
  (auditing/improvement vs. authoring/new decisions) and not straddle it.
