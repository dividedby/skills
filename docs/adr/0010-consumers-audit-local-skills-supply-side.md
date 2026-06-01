# Consumers audit their local skills (supply-side mirror of ADR 0009)

A [Consumer](../../CONTEXT.md)'s `apply-agent-research` loop performs a
**supply-side audit**: it enumerates the Consumer's own **local skills** (skills
in the repo, not published to `dividedby/skills`) and matches each against the
known skill universe — the **published catalog** (read live from the fresh
`dividedby/skills` clone the loop already makes, [ADR 0008](0008-consumers-fetch-the-skill-fresh-not-vendored.md))
**and** the **installed-skill snapshot** (`docs/agents/installed-skills.md`,
covering upstream `mattpocock/skills`). This is **one scan with three verdicts**:

- **Redundant** — the local skill duplicates a capability that already exists
  published or installed. Verdict: adopt the canonical one, retire the local
  copy. Filed into the Consumer's **own** tracker as a `source:skill-audit`
  proposal (the [per-channel cap](0011-per-channel-proposal-caps.md) applies).
- **Promotable** — the local skill matches nothing **and** clears general merit
  (broadly useful across repos, [ADR 0001](0001-buckets-cluster-by-user-intent.md)):
  it is a **promotion candidate**. Verdict: offer it up via the
  [skill-promotion channel](../design/skill-promotion-flow.md).
- **Repo-specific** — matches nothing and is not broadly useful. Verdict: keep,
  no-op.

This is the **deliberate mirror of [ADR 0009](0009-skill-request-checks-existing-and-installed-skills.md)**.
0009 is the *demand-side* already-do-this filter: it stops a Consumer
*requesting* (skill-request) a capability that already exists. The supply-side
audit reuses **the same matcher** (capability vs. `{published catalog, installed
snapshot}`) but points it at what the Consumer has *already built* rather than
what it *wishes for*, and inverts the action: a match *flags a redundant local
skill to retire*, a non-match *(plus general merit)* offers a promotion — where
0009 a match *suppresses* and a non-match *files demand*. Same matcher, opposite
ends of the supply/demand axis.

**Why.** Without it, a Consumer silently accumulates local skills that drifted
into duplicating something now published or installed (the
[ADR 0008](0008-consumers-fetch-the-skill-fresh-not-vendored.md) anti-staleness
instinct applied to whole skills, not just the loop's own code), and never
surfaces a genuinely reusable local skill for promotion — the one signal the
[ADR 0001](0001-buckets-cluster-by-user-intent.md) general-merit path needs from
the field.

**Scope.** The audit only fires when the Consumer *has* local skills; a Consumer
with none skips it. The skills repo itself has no local-non-published skills (all
its skills are published), so its own loop's audit channel is inert — but it is
the **draining/owning end** of the resulting skill-promotion offers.
