# Playbook-Driven Migration

This repo will not publish a standalone skill for guiding AI-assisted codebase
migrations from a curated before/after playbook.

## Why this is out of scope

The genuinely novel core of the proposal is real and distinct: handing the agent
a curated **before/after idiom-pair playbook** (not just API docs), plus a hard
**create-vs-refactor scope bifurcation** so the agent converts existing instances
rather than inventing new ones. That part is not owned by any existing skill.

But a standalone skill does not clear the bar, for two reasons the maintainer
stated when closing the first proposal (#84) after a grilling review:

1. **Mostly restates skills that already exist.** A 4-pillar migration skill
   re-derives surface that other skills already own:
   - ordered slicing of the migration → `to-issues`
   - the compile/commit green-gate checkpoint loop → `tdd` / `autonomous-loop`
   - verbatim error paste-back → general agent hygiene

   The genuinely new surface sits under a single pillar (the playbook +
   scope-bifurcation). Per the catalog-dilution principle, a skill whose novel
   core is one pillar is a refinement to an existing skill, not a standalone one
   — and a mostly-restating skill invites the same rebuild objection raised on
   #82.

2. **Frequency fit.** The maintainer does not run migrations often enough to
   reach for a dedicated skill; a rarely-used skill dilutes the catalog for the
   common case.

If this is revisited, the productive path is folding the novel core (curated
before/after playbook + create-vs-refactor scope precision) into an existing
skill rather than standing up a new one.

## Prior requests

- #84 — "New engineering skill: guide AI-assisted codebase migrations with a before/after playbook" (closed `not planned`, dedup-key `skill-playbook-migration`)
- #98 — "Skill request: playbook-driven migration" (requested by `dividedby/goodreads-bot`, capability `playbook-driven-migration`)
