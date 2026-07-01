---
name: apply-agent-research
disable-model-invocation: true
description: >
  Apply an external agent-research knowledge base to a repo's agent-meta: read a
  public knowledge mirror and the host repo's own CONTEXT.md / CLAUDE.md / docs/adr,
  then propose the best improvements as labeled issues — never editing, committing,
  or merging. Use when a scheduled loop or a maintainer wants to pull cross-repo
  agent practice into a repo's hooks, instruction files, CI, or skills.
---

# Apply Agent Research

This skill is the **consumer side of decentralized pull**: a repo reads the
`agent-research` knowledge base as one read-only input and proposes an
**agent-meta** improvement to itself. It is general — it never knows whose knowledge
it reads or whose repo it improves.

**It proposes; it never applies.** The only mutation it may make is filing issues.
No edits, no commits, no PRs. The producer/decider split
([ADR 0003](../../../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md))
is what makes unattended operation safe.

The **≤1-per-run cap** and **leak guard** are enforced by code, not prompt
discipline. They ship with this skill under [`lib/`](lib/) and travel wherever the
skill is installed. The mechanical details — dedup keys, the gate, the leak guard,
and the filing path — are in [proposal-flow.md](proposal-flow.md).

## Step 1 — Read the knowledge base

Clone `agent-research-knowledge` (this repo's credential-free public mirror of the
synthesized `knowledge/` tree) fresh each run. The tree is
`knowledge/<subject>/{practices,artifacts}/`; read each area's `index.md` first,
then the concept files it points to. Never clone the private `agent-research`
directly.

The knowledge base is a *source*, not a trigger: a run with nothing new in the KB
can still propose from the repo's own gaps, and a run may legitimately propose
nothing.

## Step 2 — Read the host repo's governance docs

Read `CONTEXT.md`, `CLAUDE.md`, and `docs/adr/` (and the skills, hooks, and
workflows they describe). These docs serve three roles:

- **Ethos-fit oracle** — a practice that clashes with a documented decision (an
  ADR, a CLAUDE.md rule) is not a fit; say so and drop it.
- **Already-do-this filter** — if the repo already encodes the practice, there is
  no proposal.
- **Installed-skill inventory** — `docs/agents/installed-skills.md` (when present)
  is the snapshot of capabilities in the host's global environment. A remote run
  cannot enumerate the install at run time. Treat an already-installed capability as
  present: never propose rebuilding it; the proposal is an *integration* or *novel
  use* if the inventory shows that gap.
- **Already-refused filter** — `.out-of-scope/` (when present) records capabilities
  the repo decided *not* to adopt, with reasoning and a bar-to-revisit. Never
  re-propose a capability whose file shows its bar-to-revisit is unmet. Without this
  directory, the same signal is one hop away in closed `wontfix` issue bodies.

Completion criterion: every governance doc that exists has been read; the
already-do-this and already-refused baselines are established.

## Step 3 — Map KB practices to agent-meta surfaces

Bridge the knowledge (subject-scoped practices and artifacts) to the host's
**agent-meta surfaces**: `CLAUDE.md` instructions, hooks and settings, CI
workflows, and skills. There is no static subject allow-list or routing table.

For each candidate practice ask: *which agent-meta surface here would it sharpen,
and is that surface weaker than the practice suggests it should be?* The gap is the
proposal.

## Step 4 — Supply-side audit (Consumers with local skills)

If the host has **local skills** — skills in its own repo not published to
`dividedby/skills` — enumerate each and match it against the known skill universe:
the **published catalog** (read live from the fresh `dividedby/skills` clone the
loop makes to fetch this skill,
[ADR 0008](../../../docs/adr/0008-consumers-fetch-the-skill-fresh-not-vendored.md))
and the **installed-skill snapshot**. One scan, three verdicts:

- **Redundant** (matches an existing skill) → a `source:skill-audit` candidate in
  the host's own tracker: adopt the canonical skill, retire the local copy.
- **Promotable** (no match and clears general merit,
  [ADR 0001](../../../docs/adr/0001-buckets-cluster-by-user-intent.md)) → a
  `skill-promotion` offer up to `dividedby/skills` (see
  [`skill-promotion-flow.md`](../../../docs/design/skill-promotion-flow.md)).
- **Repo-specific** (no match, not broadly useful) → keep, no-op.

This is the mirror of the demand-side already-do-this filter
([ADR 0009](../../../docs/adr/0009-skill-request-checks-existing-and-installed-skills.md)):
same matcher, pointed at what the host *already built* instead of what it
*wishes for*. A host with no local skills skips this step.

## Step 5 — Apply the adversarial pre-gate filter

Before any candidate reaches the proposal gate, challenge it on five rejection
criteria (defined in full in
[proposal-flow.md](proposal-flow.md#the-proposal-gate--run-once-over-every-channels-candidates)):

1. **Catalog overlap** — duplicates a published skill, installed skill, or wontfixed
   proposal (judged by the *principle* behind the closure, not the dedup key alone).
2. **Restatement dilution** — mostly restates what existing skills already own; the
   novel core is a refinement, not a standalone skill.
3. **Frequency fit** — the maintainer would rarely encounter this scenario.
4. **KB evidence** — the knowledge note over-generalizes beyond what it actually
   supports.
5. **Before/after concreteness** — the surface is unnamed or the change is too vague
   to implement without ambiguity.

A candidate that cannot clear all five is dropped — it does not reach the gate.

## Step 6 — Run the budgeted proposal gate and file

Gather surviving candidates from every enabled channel, tag each with its channel,
and run the gate **once** over the merged set — see [proposal-flow.md](proposal-flow.md).

Channels, each filing into the host repo's tracker unless noted:

- **self-improvement** (`source:agent-research`) — agent-meta improvements, each
  with a concrete before/after citing the KB note that motivated it.
- **skill-audit** (`source:skill-audit`) — redundant-skill findings from Step 4.
- **[skills-repo only]** — see *Skills-repo specialization* below.

The gate returns at most **one** ranked candidate. File it through the
**guarded path** (`cli.py file`), never `gh issue create` directly. Every filed body
passes the leak guard before reaching the tracker. File what the gate returned, then
stop — no second pass, no commits.

Completion criterion: gate has run exactly once; every returned candidate has been
filed through `cli.py`; nothing else has been written to any repo.

## Skills-repo specialization

The skills repo is a special consumer: its agent-meta *is* the published skills.
Beyond the base channels it also —

- **proposes skills on general merit** — a KB practice that warrants a net-new
  published skill (broadly useful per
  [ADR 0001](../../../docs/adr/0001-buckets-cluster-by-user-intent.md)), not just a
  refinement to an existing one.
- **drains incoming `skill-request` issues** — open `skill-request` issues are
  cross-repo demand. Fold the best-supported one into a proposed skill. More "+1 /
  also wanted by `<repo>`" corroboration carries more build priority — duplicate
  requests aggregate as demand
  ([ADR 0006](../../../docs/adr/0006-skill-request-demand-corroboration.md)). The
  inbound contract is in
  [`skill-request-flow.md`](../../../docs/design/skill-request-flow.md).
- **owns the `skill-promotion` label and adopts offers** — incoming
  `skill-promotion` issues are cross-repo supply: a Consumer offering a local skill
  it already built. An offer is already a concrete proposal with a reference
  implementation; the loop's only duty is to **ensure the `skill-promotion` label
  exists** (the workflow does this idempotently). See
  [`skill-promotion-flow.md`](../../../docs/design/skill-promotion-flow.md).

The self-improvement, general-merit, and skill-request-drain candidates remain
distinct channels — separate labels and destinations — but they compete in one
merged, budgeted gate pass
([ADR 0019](../../../docs/adr/0019-proposal-loops-file-a-budgeted-ranked-top-k.md)).

## Quality bar (applies to every channel)

- **Recommendations, not a menu.** Each filed issue makes one call. A forced
  finding is worse than none — if nothing clears the bar, skip and say why.
- **Concrete before/after.** Name the surface, quote what's there now in prose (not
  as pasted code or path tokens that trip the guard), and state the exact change.
- **Generalized, leak-safe.** The tracker may be public and the host private;
  describe the need so it reads as broadly useful and carries no private content.
  The guard is a backstop, not a license to skip prose discipline.
- **Cite the source.** Reference the KB note(s) so a reviewer can trace the basis.
