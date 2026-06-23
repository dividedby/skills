# Skill-authoring lore lives in docs/agents/, not a code indexer

The *craft* of authoring a skill here is scattered and re-derived each loop:
the "prescribe principles, not literal code" edge cases ([ADR 0002](./0002-design-skills-prescribe-at-principle-level.md), #12)
are re-argued per skill; cross-skill composition decisions (which wrapper calls
which sub-skill) live implicitly in the wrappers; `.out-of-scope/` rejection
rationales are re-argued when a similar idea returns.

## Context

Two related ideas were drained from the Idea Inbox (#91) and decision-mapped into
a spike (#400):

1. A **skill-authoring lore wiki** (Karpathy "LLM Wiki" lens) to capture the
   re-derived craft.
2. A **codebase-memory verdict**: a `/cba-searching` + `/grilling` pass concluded
   a **code indexer is overkill** here — symbol-nav pain is low (a ~5.4k-line
   Python harness plus markdown skills, no god modules), and "where things live"
   is already the top-level `README` catalog plus per-skill `SKILL.md`.

Candidate hosts for the lore: Serena markdown memories (repo `.serena/memories/`
or global `~/.serena/memories/global/`); a `docs/` knowledge tree; or folding it
into an existing surface (`installed-skills.md` / `setup-dividedby-skills`).

## Decision

**Skill-authoring lore lives in `docs/agents/skill-authoring.md`** — a committed,
in-repo doc, not Serena memories and not a code index.

- The deciding constraint is the same one that put a committed snapshot at
  `docs/agents/installed-skills.md`: the lore must be readable by **headless /
  remote loops that clone the repo**. Global Serena memories live in no repo;
  even repo memories are not the human-/loop-browsable convention surface.
  Authoring lore being cross-repo *argues for global* — exactly what a remote
  single-repo clone cannot see. `docs/agents/` is in-repo, git-versioned,
  GitHub-browsable, loop-readable, and matches the established convention-doc
  pattern.
- Folding into `installed-skills.md` / `setup-dividedby-skills` is the wrong
  semantic home (capability snapshot ≠ authoring craft) and conflates concerns.
- A Serena memory **may mirror** the doc for in-session convenience, but the
  committed doc is canonical.

**Scope (ponytail):** start as the single file `docs/agents/skill-authoring.md`;
grow to a `docs/agents/skill-authoring/` tree (index + append-only log) only if
it earns it.

**First synthesis seeds two sections, defers two:**

- **Composition-pattern catalog** — when to call which sub-skill, with file refs
  (e.g. `software-design` → `codebase-design`/`domain-modeling`; `grill-with-docs`
  → `grilling` + `domain-modeling`). Highest unique value: nothing captures it
  today.
- **Editorial-judgement log** — worked ADR 0002 edge cases ("prescribe principles,
  not literal code"), the most-cited recurring re-argument; source = ADR 0002, #12.
- **Deferred:** a rejection runbook and an antipattern collection — both overlap
  `.out-of-scope/`, which already partially serves that role. Revisit when
  rejection rationales get re-argued *despite* `.out-of-scope/`.

**No-code-indexer verdict (recorded so it is not re-proposed):** a code indexer /
code-graph is overkill here. **Revisit trigger:** the `harness/` Python grows to
where symbol-nav pain is real.

**No overlap with `skill-divergence-audit`:** that audit watches *external* drift
(this repo's skills vs. mattpocock's). Skill-authoring lore is *internal*
authoring craft. Different concerns; no consolidation.

## Consequences

- A new convention doc joins `docs/agents/`: `skill-authoring.md`. Implementation
  is a downstream `ready-for-agent` ticket (gated on this ADR), not part of the
  spike.
- The spike (#400) is resolved by this ADR and closed.
- If a code indexer is ever proposed again, this ADR is the standing answer until
  the revisit trigger fires.
