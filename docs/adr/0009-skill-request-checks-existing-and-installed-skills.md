# skill-request filing checks existing and installed skills first

Before a [Consumer](../../CONTEXT.md) files a `skill-request` into
`dividedby/skills`, its loop checks the candidate capability against the
**existing published skills** (the `skills/` catalog of the freshly-cloned
`dividedby/skills`) **and** the maintainer's installed-skill snapshot
(`docs/agents/installed-skills.md`) — treating either as already-do-this — not
just the open `skill-request` issues. This extends
[ADR 0007](0007-already-do-this-baseline-includes-installed-skills.md) from the
skills-repo's own loop to the cross-repo Consumer (Channel-2) path.

Why: without it a Consumer re-requests capabilities that already ship or are
already installed. `dividedby/skills#51` asked for a progressive-alignment
"grilling" skill that `grill-me`/`grill-with-docs` already provide — and those
are installed upstream from `mattpocock/skills`, not even in this repo's own
catalog. Matching open `skill-request` issues alone cannot catch that.

Mechanism note (live catalog vs. snapshot): the **published catalog** is read
**live from the fresh clone** the Consumer already makes to fetch the skill
([ADR 0008](0008-consumers-fetch-the-skill-fresh-not-vendored.md)) — no snapshot
needed, because a public repo is enumerable at run time. The **installed set**
still comes from the committed `installed-skills.md` snapshot, because a remote CI
run cannot enumerate the maintainer's private global install (the original ADR
0007 constraint). Two surfaces, two mechanisms, one already-do-this rule.
