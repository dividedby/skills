---
feature: skill-promotion-flow
status: accepted
---

# Design: the `skill-promotion` supply channel

How a [Consumer](../../CONTEXT.md) that has built a **local skill** broadly
useful enough to publish offers it **up** to `dividedby/skills` for adoption.
This is the **supply twin** of the [`skill-request` demand channel](./skill-request-flow.md):
same destination repo, same cross-repo machinery, **inverse semantics**. Read
`skill-request-flow.md` first — this doc is deliberately thin and states only
where promotion *differs*.

## Demand vs supply, in one line

- **skill-request** = "build this, it does **not** exist" (demand).
- **skill-promotion** = "this **already** exists — I built it — adopt it" (supply).

A promotion is sourced not from a wished-for gap but from the **supply-side
audit** ([ADR 0010](../adr/0010-consumers-audit-local-skills-supply-side.md)):
when the audit judges a local skill *promotable* (matches no published/installed
skill **and** clears general merit, [ADR 0001](../adr/0001-buckets-cluster-by-user-intent.md)).

## Who triggers it

The `apply-agent-research` loop's supply-side audit, in any Consumer that has
local skills. The skill-promotion filing is its own [per-channel](../adr/0011-per-channel-proposal-caps.md)
output (≤1 per run), distinct from the self-improvement, skill-audit, and
skill-request channels.

## Reused unchanged from `skill-request-flow.md`

- **The cross-repo write token.** The same per-Consumer fine-grained PAT
  (`SKILLS_TRACKER_TOKEN`, `Issues: Read and write` on `dividedby/skills` only).
  No new credential — promotion is another issue write into the same repo.
- **The capability key + `+1` aggregation.** Match on `<!-- capability: <slug> -->`
  against **open `skill-promotion`** issues: no match → file; match → comment
  `+1 — also built by <repo>`. Here `+1` is an unusually strong signal — two repos
  *independently building the same skill* is hard evidence of general merit, not
  mere demand.
- **The leak guard.** The filed `title + body` passes `cli.py sanitize` with the
  host's private markers. This matters more than for any other channel: a private
  Consumer's local `SKILL.md` is the very thing being offered, so its name,
  paths, and identifiers must be generalized — describe the *capability*, point
  to where the implementation lives, never paste it.
- **Label ownership.** `dividedby/skills` **owns** the `skill-promotion` label
  (created/re-ensured idempotently by the draining workflow); Consumers only
  *apply* it, never create it.
- **Re-proposable closes.** Matching is over *open* issues only, so a close is
  not durable suppression — a stronger later offer re-files.

## The issue contract

A `skill-promotion` issue in `dividedby/skills`, carrying the `skill-promotion`
label, must justify *adoption of a working skill*. It states:

- **Capability offered** — what the skill does, generalized / leak-safe.
- **Why it clears general merit** — broadly useful across repos
  ([ADR 0001](../adr/0001-buckets-cluster-by-user-intent.md)), and **skill-shaped**
  rather than a run-book the offering repo should keep or a harness feature (the
  same skill-shaped check as a skill-request).
- **Where the implementation lives** — a pointer the maintainer can open (repo /
  skill path), not a paste of the body.
- **Not already covered** — confirming the audit's non-match against the
  published catalog and `docs/agents/installed-skills.md`. (If it *were* covered,
  the audit's verdict would be *redundant*, not *promotable*.)
- **Offering repo** — which Consumer built it.
- The stable `<!-- capability: <slug> -->` marker.

## Where it differs on the draining end (asymmetry with demand)

A **skill-request** must be *folded* into a proposed skill — demand is raw, the
maintainer still has to design and write the skill. A **skill-promotion is
already a concrete proposal with a reference implementation**: it is directly
human-actionable in `dividedby/skills`. So:

- The skills-repo loop does **not** need a "drain promotions" candidate source
  the way it drains demand into a `source:agent-research` proposal. The
  `skill-promotion` issue **is** the deliverable; the maintainer reviews it and
  adopts (writes/imports the skill, registering it in `plugin.json` + `README.md`)
  or declines.
- The skills-repo workflow's only mechanical duty is to **ensure the
  `skill-promotion` label exists** (idempotently, alongside `skill-request`).

## What lives where

- **In `dividedby/skills` (this repo):** the `skill-promotion` label (owned
  here), this contract, [ADR 0010](../adr/0010-consumers-audit-local-skills-supply-side.md),
  and the human-review/adopt end.
- **In each Consumer repo:** the supply-side audit + the file-or-`+1` filing
  step inside its own `apply-agent-research` workflow, using `SKILLS_TRACKER_TOKEN`.
  Built per Consumer at onboarding (see
  [`docs/onboarding/consumer-setup.md`](../onboarding/consumer-setup.md)).

## Invariants

- A promotion is **supply, never demand** — only a local skill that *already
  exists* and clears general merit; never a wish.
- Reuses the skill-request token, capability key, `+1`, and leak guard; differs
  only in label, semantics, and the lighter draining end.
- `dividedby/skills` owns the `skill-promotion` label; Consumers apply, never
  create.
- Adoption is still the maintainer's decision (producer/decider,
  [ADR 0003](../adr/0003-skill-improvement-workflows-propose-via-issues.md)); the
  loop offers, the human adopts.
