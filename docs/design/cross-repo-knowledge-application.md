---
feature: cross-repo-knowledge-application
status: proposed
supersedes: skill-improvement-workflows
---

# Design Plan: cross-repo knowledge application (`apply-agent-research`)

How a repo applies the `agent-research` knowledge base to improve its own
agent-meta. This is the consumer-side realization of agent-research
**ADR 0019** ("knowledge is consumed via decentralized pull"), which named
this file as its home. It **supersedes** the central-push design in
[`skill-improvement-workflows.md`](./skill-improvement-workflows.md) (the
VPS-hosted self-improvement + gap-scanner run-books, never wired). See
[ADR 0003](../adr/0003-skill-improvement-workflows-propose-via-issues.md) (and
its decentralized-pull amendment) for the producer/decider model and `CONTEXT.md`
for `Run-book`, `Knowledge mirror`.

## The shape: pull, not push

Old model: a central engine on the VPS read the KB and *pushed* proposals into
consumers. New model: each **Consumer** repo runs its own loop, reads the KB as
one read-only input, and proposes changes **to itself**. agent-research holds no
model of any consumer. The shared mechanism is a published skill,
**`apply-agent-research`**, that any consumer installs; the per-repo schedule
that fires it is a thin **run-book** wrapper (see `CONTEXT.md` — capability is a
skill, the schedule is a run-book).

## The skill: `apply-agent-research`

A **published** skill (registered in `plugin.json`), general across consumers —
it never knows it is reading Matt's KB or improving Connor's skills. Its generality
is what makes it plugin-worthy (ADR 0001) and reverses ADR 0003's "not a skill,
too narrow" stance for this case (see the ADR 0003 amendment).

- **Reads (input):** the **public knowledge mirror** (shallow clone, no
  credential — see below), and the **host repo's own** `CONTEXT.md` / `CLAUDE.md`
  / `docs/adr/`. The host's own governance docs are both the *ethos-fit oracle*
  ("would this fit how this repo works?") and the *already-do-this filter*
  ("does this repo already do this?"). The consumer maps subject-scoped knowledge
  to its own concerns at run time — there is no static subject allow-list.
- **Writes (output):** at most **one issue per run** into the host repo's own
  tracker, provenance label **`source:agent-research`**, proposing an agent-meta
  improvement. It **never auto-applies**: no skill edits, no PRs, and — unlike the
  old model — **no commits at all** (the integration map that was the one allowed
  auto-commit is dropped). Pure read → file issue.
- **Dedup + cap:** reads back the open `source:agent-research` issues and runs
  the surviving candidate through `proposal_gate` (≤1/run, exact-key dedup,
  `wontfix`-suppression).
- **Leak guard:** every filed `title + body` passes `sanitizer.check()` first.
  The KB is public now, so the guard's job is no longer protecting the KB — it
  protects against leaking the **host repo's own** private content into a public
  tracker (load-bearing when the host is private, or for `skill-request`).

## Knowledge mirror (credential-free reads)

The skill reads a **public, read-only mirror** of agent-research's synthesized
`knowledge/` (see `CONTEXT.md`), not the private repo. This dissolves the
credential problem that drove the old VPS decision: there is **no private token
in public Actions** anywhere. Only the distilled `knowledge/` is mirrored; raw
`sources/` never leave the private repo.

**Cross-repo dependency (agent-research owns):** stand up the public mirror repo,
add a verbatim `knowledge/` → mirror push (commit-if-changed) to the synthesize
workflow, and **amend agent-research ADR 0019** — a verbatim, unopinionated mirror
is a *transport/visibility* change, not the curated/opinionated bundle that ADR
rejected. Until the mirror exists, the documented fallback is a read-only deploy
key in skills' GHA secrets (narrow: secrets are not exposed to fork-PR workflows;
only the maintainer triggers `main`/scheduled runs).

## Runtime: the skills repo's own loop

The skills repo is one Consumer. Its loop runs as **its own scheduled GitHub
Actions workflow**, modeled on `.github/workflows/improve-codebase-architecture.yml`:
checkout (own governance docs + skills are then local), shallow-clone the public
mirror, ensure the `source:agent-research` label idempotently, run the skill,
file ≤1 issue via the own-repo `GITHUB_TOKEN` (`issues:write`). No private
cross-repo credential; the VPS is not involved (agent-research ADR 0016).
`apply-agent-research` lives in this repo, so no external install step is needed
(unlike arch-review, which installs its skill from `mattpocock/skills`).

## Reused / deprecated modules

- **Survive (pure, tracker-agnostic):** `proposal_gate` (≤1/run + dedup),
  `sanitizer` (structural leak guard). Both are invoked by the skill.
- **Deprecate (tied to the central-push topology) — leave in place, marked
  superseded, until `apply-agent-research` lands, so there is never a window with
  neither:** `map_store` (map dropped), `self_improvement` orchestrator (folded
  into the skill), `kb_source` + `kb-source.json` (no static allow-list — runtime
  relevance judgment instead), `repo_scan` + `gap_scanner` (gap-scanner superseded
  by the `skill-request` flow).

## `skill-request` — named here, designed later

The gap-scanner's function (detect that other repos need a net-new skill) moves
to **decentralized demand**: a Consumer running `apply-agent-research` on itself,
finding it needs a capability the skills repo lacks, files a **`skill-request`**
issue into the skills tracker; duplicate requests *aggregate* as demand signal
(legitimate cross-repo demand corroboration, distinct from the knowledge-claim
corroboration ADR 0018 forbids). This flow is **out of scope here** and deferred
to its own design — it carries open questions this doc does not settle: the
cross-repo write token (own-repo `GITHUB_TOKEN` cannot file into another repo;
needs a PAT/App token), demand-aggregation/dedup semantics, and who triggers it.

## Invariants

- At most one issue per run (the gate enforces it; zero is fine).
- The skill writes nothing to the repo — proposes via issues only, never merges
  or commits.
- Filed issues are generalized and pass the structural `sanitizer` — no host
  private content into a public tracker.
- agent-research never depends on this repo; the dependency arrow is one-way.

## Open / deferred

- The full `skill-request` design (above).
- The agent-research mirror implementation + its ADR 0019 amendment (cross-repo
  dependency, above).
- Build sequencing for the skill + the skills-repo workflow (a later to-issues pass).
