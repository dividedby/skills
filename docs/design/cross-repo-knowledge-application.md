---
feature: cross-repo-knowledge-application
status: accepted
supersedes: skill-improvement-workflows
---

# Design: cross-repo knowledge application (`apply-agent-research`)

How a repo applies the `agent-research` knowledge base to improve its own
agent-meta. This is the consumer-side realization of agent-research
**ADR 0019** ("knowledge is consumed via decentralized pull"), which named
this file as its home. It **supersedes** the central-push design in
[`skill-improvement-workflows.md`](./skill-improvement-workflows.md) (the
VPS-hosted self-improvement + gap-scanner run-books, never wired). See
[ADR 0003](../adr/0003-skill-improvement-workflows-propose-via-issues.md) (and
its decentralized-pull amendment) for the producer/decider model and `CONTEXT.md`
for `Run-book`, `Knowledge mirror`, `Consumer`.

This file is the **authoritative cross-repo overview** — it orients a reader and
points at the canonical docs, which own the mechanics:

- **Demand channel** (`skill-request`) → [`skill-request-flow.md`](./skill-request-flow.md),
  [ADR 0006](../adr/0006-skill-request-demand-corroboration.md),
  [ADR 0009](../adr/0009-skill-request-checks-existing-and-installed-skills.md).
- **Supply channel** (`skill-promotion`) → [`skill-promotion-flow.md`](./skill-promotion-flow.md),
  [ADR 0010](../adr/0010-consumers-audit-local-skills-supply-side.md).
- **Per-channel caps** → [ADR 0011](../adr/0011-per-channel-proposal-caps.md).
- **Fetch-fresh / installed-skill baseline** → [ADR 0007](../adr/0007-already-do-this-baseline-includes-installed-skills.md),
  [ADR 0008](../adr/0008-consumers-fetch-the-skill-fresh-not-vendored.md).
- **Standing up a Consumer** → [`docs/onboarding/consumer-setup.md`](../onboarding/consumer-setup.md),
  [`docs/onboarding/proposal-loop-harness.md`](../onboarding/proposal-loop-harness.md).

## The shape: pull, not push

Old model: a central engine on the VPS read the KB and *pushed* proposals into
consumers. New model: each **Consumer** repo runs its own loop, reads the KB as
one read-only input, and proposes changes **to itself** (and, for cross-repo
channels, into `dividedby/skills`). agent-research holds no model of any
consumer. The shared mechanism is a published skill, **`apply-agent-research`**,
that any consumer installs; the per-repo schedule that fires it is a thin
**run-book** wrapper (see `CONTEXT.md` — capability is a skill, the schedule is a
run-book).

## The skill: `apply-agent-research`

A **published** skill (registered in `plugin.json`), general across consumers —
it never knows it is reading Matt's KB or improving Connor's skills. Its generality
is what makes it plugin-worthy (ADR 0001) and reverses ADR 0003's "not a skill,
too narrow" stance for this case (see the ADR 0003 amendment).

- **Reads (input):** the **public knowledge mirror** (shallow clone, no
  credential — see below); the **host repo's own** `CONTEXT.md` / `CLAUDE.md`
  / `docs/adr/`; the **published skills catalog** (read live from the fresh
  `dividedby/skills` clone the loop already makes,
  [ADR 0008](../adr/0008-consumers-fetch-the-skill-fresh-not-vendored.md)); and
  the host's **installed-skill snapshot** (`docs/agents/installed-skills.md`).
  Together the host's governance docs and the catalog+installed inventory are
  both the *ethos-fit oracle* ("would this fit how this repo works?") and the
  *already-do-this filter* ("does this repo already do or have this?",
  [ADR 0007](../adr/0007-already-do-this-baseline-includes-installed-skills.md) /
  [ADR 0009](../adr/0009-skill-request-checks-existing-and-installed-skills.md)).
  The consumer maps subject-scoped knowledge to its own concerns at run time —
  there is no static subject allow-list.
- **Fetched fresh, never vendored:** a Consumer without a plugin system obtains
  the skill by fetching it from `dividedby/skills` each run, not by committing a
  frozen copy — so the leak guard and gate (which are *code*, not prompt
  discipline) never go stale
  ([ADR 0008](../adr/0008-consumers-fetch-the-skill-fresh-not-vendored.md)).
- **Writes (output):** proposes via the tracker only. It **never auto-applies**:
  no skill edits, no PRs, and **no commits at all** (the integration map that was
  the one allowed auto-commit is dropped). Pure read → file issue.
- **One budgeted gate pass across all channels:** the run files at most **one
  issue total**, picked best-first by a single gate pass over every enabled
  channel's merged candidates
  ([ADR 0019](../adr/0019-proposal-loops-file-a-budgeted-ranked-top-k.md),
  superseding the per-channel one-cap of ADR 0011). One is a ceiling, not a
  target — the candidate must independently clear the old single-best bar, and
  a typical run files 0–1. The "no menu" discipline still holds per issue.
- **Leak guard:** every filed `title + body` passes `sanitizer.check()` first.
  The KB is public, so the guard's job is no longer protecting the KB — it
  protects against leaking the **host repo's own** private content into a public
  tracker (load-bearing when the host is private, or for `skill-request`).

## Channels

A single run can file at most one issue total across the applicable channels
(zero is the common case). The channels target different concerns and, for the
cross-repo pair, different repos — they share one ranked budget
([ADR 0019](../adr/0019-proposal-loops-file-a-budgeted-ranked-top-k.md)):

| Channel | Label | Destination | Basis |
|---|---|---|---|
| **self-improvement** | `source:agent-research` | Consumer's own tracker | a KB knowledge note |
| **skill-audit** | `source:skill-audit` | Consumer's own tracker | local skill duplicates the published/installed catalog ([ADR 0010](../adr/0010-consumers-audit-local-skills-supply-side.md)) |
| **general-merit skill** *(skills repo only)* | `source:agent-research` | own tracker | a KB note warranting a net-new published skill |
| **skill-request** *(demand)* | `skill-request` | `dividedby/skills` | a felt gap with no existing skill ([flow](./skill-request-flow.md)) |
| **skill-promotion** *(supply)* | `skill-promotion` | `dividedby/skills` | a promotable local skill ([flow](./skill-promotion-flow.md)) |

The two cross-repo channels are mirror images on the supply/demand axis: the
**supply-side audit** ([ADR 0010](../adr/0010-consumers-audit-local-skills-supply-side.md))
enumerates a Consumer's own local skills and matches each against the
published+installed universe — a match flags a *redundant* local skill to retire,
a non-match that clears general merit becomes a *promotion* offer — reusing the
same matcher as the demand-side already-do-this filter
([ADR 0009](../adr/0009-skill-request-checks-existing-and-installed-skills.md))
but inverting the action. Duplicate `skill-request`s **aggregate** as demand
signal rather than being suppressed
([ADR 0006](../adr/0006-skill-request-demand-corroboration.md)); usefulness of a
*built* skill is still settled by adoption, not by request count.

## Knowledge mirror (credential-free reads)

The skill reads a **public, read-only mirror** of agent-research's synthesized
`knowledge/` (`dividedby/agent-research-knowledge`, see `CONTEXT.md`), not the
private repo. This dissolves the credential problem that drove the old VPS
decision: there is **no private token in public Actions** anywhere. Only the
distilled `knowledge/` is mirrored; raw `sources/` never leave the private repo.
The loop re-clones the mirror fresh each run (`git clone --depth 1`, no
credential), so refreshed knowledge is applied promptly.

## Runtime: the skills repo's own loop

The skills repo is one Consumer. Its loop runs as **its own scheduled GitHub
Actions workflow** ([`.github/workflows/apply-agent-research.yml`](../../.github/workflows/apply-agent-research.yml)):
checkout (own governance docs + skills are then local), shallow-clone the public
mirror, ensure the channel labels idempotently, run the skill, file the gate's ≤5
budgeted issues via the own-repo `GITHUB_TOKEN` (`issues:write`). No private cross-repo
credential; the VPS is not involved (agent-research ADR 0016).
`apply-agent-research` lives in this repo, so no external install step is needed
(unlike arch-review, which installs its skill from `mattpocock/skills`). Other
Consumers fetch the skill fresh instead — see
[`consumer-setup.md`](../onboarding/consumer-setup.md).

## Invariants

- At most one issue **per channel** per run (the gate enforces it; zero is fine).
- The skill writes nothing to the repo — proposes via issues only, never merges
  or commits.
- Filed issues are generalized and pass the structural `sanitizer` — no host
  private content into a public tracker.
- agent-research never depends on this repo; the dependency arrow is one-way.
