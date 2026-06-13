# arch-review fetches the depth rubric fresh from an external upstream and adds local simplification + legibility lenses

## Context

[ADR 0016](0016-arch-review-prompt-is-skeleton-plus-local-repo-context-include.md)
established the arch-review prompt as a fetched-fresh, scope-free skeleton paired
with a per-repo Repo-context include. At that time the skeleton **hand-modeled the
depth concepts** — deep/shallow modules, seams, the deletion test — as prose. This
worked but created drift: the installed copy of mattpocock's
`improve-codebase-architecture` skill is a frozen snapshot; whenever mattpocock
evolves the depth rubric, the skeleton falls behind without any signal.

[ADR 0014](0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md)
established the fetch-fresh rail for the harness, targeting the harness's own
`dividedby/skills` repo. This ADR generalizes that pattern to an **external**
upstream (`mattpocock/skills`).

Additionally:

- [Issue #112](https://github.com/dividedby/skills/issues/112) requested an
  agent-legibility audit — flagging physical legibility problems (oversized files,
  naming, greppability, CLI surface) that no existing lens captured. Delivering
  this as a new standalone skill would add an interactive wrapper around a
  demand that is loop-shaped; the arch-review loop is the right delivery vehicle.
- The ponytail over-engineering discipline (five categories: delete, stdlib,
  native, yagni, shrink) had no home in the arch-review loop. Simplification is
  the natural first pass before deepening.

## Decision

**(a) The skeleton stops modeling depth concepts in prose.** The workflow
fetches `mattpocock/skills` `LANGUAGE.md` and `DEEPENING.md` fresh at run time
and appends them to the system prompt between the skeleton and the local
Repo-context include. The skeleton's Depth lens section forward-references the
appended rubric — the same forward-reference pattern the Scope section uses for
the Repo-context include. This generalizes ADR 0014's fetch-fresh principle to
an external third-party upstream.

**(b) Pin policy is FLOAT `main`, not a pinned SHA.** Each run pulls mattpocock's
latest depth thinking automatically, and no drift accumulates. The accepted
tradeoff: an external party's edits enter the unattended loop unreviewed each
run. This is a deliberate maintainer choice made against the recommendation to
pin; consumers who need review-before-run should override the pin in their own
envelope.

**(c) Fetch failure hard-fails the run.** Consistent with ADR 0016's missing-include
gate: an unattended run with a missing or partial depth rubric would produce
unsound depth proposals, which is worse than a clean failure. The workflow fetches
both files in a dedicated step before invoking the agent and exits non-zero with a
clear message on any curl error.

**(d) Two new local lenses are added to the skeleton at principle level** (ADR 0002
— prescribe at the principle level):

- **Simplification** (first) — five principle-level categories from the ponytail
  discipline: delete, stdlib, native, yagni, shrink. Modeled in the skeleton as
  prose, not fetched, because: the ponytail-review skill is a tiny, stable,
  diff-format-coupled checklist whose five tenets are cheaper to inline than to
  fetch (fetch-fresh pays for large, evolving concept files, not a short checklist).
- **Legibility** (third, after depth) — four physical-structure dimensions: oversized
  files, non-conventional names, weak greppability, and gated CLI surfacing. Modeled
  in the skeleton as prose because there is no upstream source to fetch it from —
  this is a new concept, not a copy of an existing skill's rubric.

**(e) Three-lens precedence, one finding per lens, lens tag in proposal body.**
Lenses run in order: simplification → depth → legibility. A finding belongs to
exactly one lens; precedence resolves contradictions (simplification beats depth,
depth beats legibility). Every emitted proposal body carries a
`<!-- lens: simplification|depth|legibility -->` HTML-comment marker alongside the
existing `<!-- capability: … -->` and `<!-- dedup-key: … -->` markers. No new
GitHub label is added.

## Consequences

- **Depth tracks mattpocock automatically** — no manual skeleton edits when the
  rubric evolves; the skeleton stays thin and focused on the envelope logic.
- **An upstream rename or deletion surfaces as a hard-fail** — the fetch step exits
  non-zero and the run fails loudly, rather than silently using an outdated rubric.
- **All three lenses ship to consumers via the shared skeleton.** A Consumer who
  adopts the loop gets simplification, depth, and legibility out of the box without
  any local changes beyond shipping their Repo-context include.
- **Issue #112 is delivered as a workflow change**, not a standalone skill.
  The legibility lens lives where its demand is: in the unattended loop, not a
  separately invokable skill with no interactive use case.
- **Supply-chain risk accepted.** The float policy means a third-party maintainer's
  changes enter unattended runs unreviewed. See the onboarding doc for the
  recommendation to pin if that tradeoff is unacceptable downstream.

## Rejected alternatives

- **Invoke mattpocock's skill directly** — the skill's output is shaped for an
  interactive HTML workflow and its installer assumes a user-accessible `~/.claude`
  directory; neither fits an unattended CI loop. The rubric files are the useful
  artifact; the skill wrapper is not.
- **Pin a SHA** — the maintainer explicitly chose float to track mattpocock's
  latest thinking automatically. A pinned SHA would require a manual bump on every
  upstream change, recreating the drift problem this ADR exists to solve.
- **A standalone legibility skill** — demand is loop-shaped; there is no interactive
  use case for a one-shot legibility audit without a human session. Delivering it
  as a workflow lens avoids adding an invokable skill nobody would call.
- **CBA-searching as a fourth lens** — external prior-art comparison is the wrong
  job for this loop; it would belong to a research-oriented loop, not an in-repo
  structural review. Filed to the Idea Inbox for future consideration.
