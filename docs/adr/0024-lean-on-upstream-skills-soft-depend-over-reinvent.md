# Lean on Matt Pocock's upstream skills; default to delete-and-soft-depend over reinvention

> **Amendment (2026-07-02) — second upstream: `anthropics/claude-plugins-official`.** This
> ADR's contract — delete + soft-depend first, thin wrapper only when justified, compose by
> reference — was written against `mattpocock/skills` alone. The official catalog is now a
> second upstream to evaluate skill-by-skill against the same preference order: it is already
> in the maintainer's installed baseline ([`docs/agents/installed-skills.md`](../agents/installed-skills.md)),
> so overlap is a live question, not a hypothetical. Nothing about the contract changes —
> only its scope, from one upstream to two. `CONTEXT.md` "Upstream soft-dependencies" and
> `README.md` "Upstream" name both.

## Context

This repo (`dividedby/skills`) was conceived to **extend** `mattpocock/skills` and fill genuine gaps —
not to replace it. Matt has since significantly revamped his repo: new foundational skills
(`codebase-design`, `domain-modeling`, `writing-great-skills`), rebuilt skills
(`diagnosing-bugs`, `resolving-merge-conflicts`, `ask-matt` router), and his own `triage` +
`setup-matt-pocock-skills` that now parallel ours. Several of our skills overlap his revamped
foundation; some are likely reinvention.

This repo also ships as a distributable Claude Code plugin (`.claude-plugin/plugin.json`).
That means depending on Matt's plugin is a **cross-plugin architectural commitment**, not a
private convenience — it needs to be stated explicitly.

Prior ADRs have applied an upstream-reuse principle piecemeal across the loop and proposal
machinery:
[ADR 0005](./0005-software-design-runs-after-to-issues.md) — `software-design` composes on
Matt's `to-prd`/`to-issues`/`tdd` rather than reimplementing them;
[ADR 0007](./0007-already-do-this-baseline-includes-installed-skills.md) — the
installed-skill inventory is the already-do-this baseline;
[ADR 0008](./0008-consumers-fetch-the-skill-fresh-not-vendored.md) — fetch fresh, do not
vendor;
[ADR 0010](./0010-consumers-audit-local-skills-supply-side.md) — the supply-side audit
retires duplicates;
[ADR 0020](./0020-arch-review-fetches-depth-rubric-fresh-and-adds-simplification-legibility-lenses.md) —
`arch-review` fetches Matt's depth rubric fresh, thin local lenses only;
[ADR 0021](./0021-skill-request-triage-runs-external-prior-art-scan.md) — prior-art scan
before creating. 0024 extends that same upstream-reuse principle from the loop machinery to
the **skill catalog itself**.

## Decision

**Posture:** lean on Matt's foundation; keep this repo's differentiated automation and
convention skills as independent value.

**Dependency contract** (in order of preference):

1. **Delete + soft-depend** (default) — if Matt's upstream skill covers the capability,
   delete our version and document an install-alongside expectation. No local copy.
2. **Thin wrapper** — keep only when the `dividedby` glue is substantial enough to justify a
   local file. Bias toward fewer wrappers.
3. **Compose by reference** — when building on Matt's skills, reference existing pieces over
   forking (compose-by-reference, not vendoring), consistent with
   [ADR 0008](./0008-consumers-fetch-the-skill-fresh-not-vendored.md).

**Authoring standard:** every kept or reworked skill in this repo is rewritten to the
`writing-great-skills` standard.

**Soft-dependency definition:** a soft-dependency is a documented install-alongside
expectation stated in `CONTEXT.md` and `README.md` — never vendored copies. Because this
repo is a distributable plugin, the contract surface is documentation, not code.

This ADR supersedes none of the prior ADRs listed above; it generalizes and names the
principle they each applied in a narrower domain.

## Consequences

- Per-skill keep/delete/thin-wrapper verdicts (Phases 1–4 of the epic) all follow this
  contract; the verdict for each skill is recorded there, not here.
- Issue #294's original intent (uninstall Matt's `setup-matt-pocock-skills` and `triage`) is
  superseded — we now want `setup-matt-pocock-skills` kept as a soft-dependency alongside
  our own `setup-dividedby-skills` and `triage`.
- The `## Upstream soft-dependencies` section in `CONTEXT.md` and the `## Upstream` section
  in `README.md` are the contract's living surface; they are updated as per-skill verdicts
  land.
- Consumers reading this repo's installed-skill snapshot (`docs/agents/installed-skills.md`)
  will see Matt's skills listed — the snapshot is the ground truth for remote loops.
