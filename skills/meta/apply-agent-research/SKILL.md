---
name: apply-agent-research
description: >
  Apply an external agent-research knowledge base to a repo's own agent-meta:
  read a public knowledge mirror plus the host repo's own CONTEXT.md / CLAUDE.md
  / docs/adr, then propose at most one improvement as a labeled issue — never
  editing, committing, or merging. Use when a scheduled loop (or a maintainer)
  wants to pull cross-repo agent practice into this repo's hooks, instruction
  files, CI, or skills, proposing via the tracker for a human to decide.
---

# Apply Agent Research

This skill is the **consumer side of decentralized pull**: a repo reads the
`agent-research` knowledge base as one read-only input and proposes an
**agent-meta** improvement *to itself*. It is general — it never knows whose
knowledge it reads or whose repo it improves. The knowledge base is a *source*,
not a trigger: a run with nothing new in the KB can still propose from the repo's
own gaps, and a run may legitimately propose nothing.

It **proposes, it never applies.** The only mutation it may make is filing **at
most one** issue. No skill edits, no PRs, **no commits** — the producer/decider
split (see [ADR 0003](../../../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md))
is what makes unattended operation safe. A human reviews the issue and decides.

See [proposal-flow.md](proposal-flow.md) for the mechanical flow — dedup keys, the
leak guard and one-proposal gate, and the issue body shape.

The leak guard and the gate are enforced by code, not prompt discipline: the skill
**bundles** them under [`lib/`](lib/) (the pure `sanitizer` / `proposal_gate`
decisions and a `cli.py` seam), so they travel with the skill wherever it is
installed and run by file path — `python3 <skill-dir>/lib/cli.py …`. Stdlib-only,
unit-tested under [`tests/`](tests/)
(`python3 -m unittest discover -s <skill-dir>/tests`). See the
[ADR 0004 amendment](../../../docs/adr/0004-runbook-helpers-are-python-stdlib.md)
for why they live here rather than in a separate `runbooks/` dir.

## Inputs

- **The public knowledge mirror** — a credential-free, read-only clone of
  `agent-research`'s synthesized `knowledge/` tree (in this repo's instance:
  `dividedby/agent-research-knowledge`). Shallow-clone it fresh each run. The tree
  is `knowledge/<subject>/{practices,artifacts}/`; read each area's `index.md`
  first, then range over the concept files it points to. Never clone the private
  `agent-research` directly — the mirror is the whole point of the credential-free
  design. The curated cross-subject concern index is deferred; do not expect one.
- **The host repo's own governance docs** — `CONTEXT.md`, `CLAUDE.md`, and
  `docs/adr/` (and the skills/hooks/workflows they describe). These serve **two
  roles at once**:
  - **Ethos-fit oracle** — "would this fit how *this* repo works?" A practice that
    clashes with a documented decision (an ADR, a CLAUDE.md rule) is not a fit;
    say so and drop it rather than proposing against the grain.
  - **Already-do-this filter** — "does this repo *already* do this?" If the repo
    already encodes the practice, there is no proposal. This replaces the old
    integration map: the repo's own docs are the baseline.
  - **Installed-skill inventory (if the host maintains one)** — the repo's own
    `skills/` is not the whole picture: capabilities installed in the host's
    environment are available in every session even when not files here. If the
    host commits an inventory of them (this repo: `docs/agents/installed-skills.md`),
    read it as part of the already-do-this baseline. A remote run cannot enumerate
    the install at run time, so this committed snapshot is the only signal it has.
    **Treat an already-installed capability as present, not absent** — never
    propose rebuilding it. The proposal there is an *integration* or *novel use*
    with this repo's own skills, if the inventory shows that gap.

## The mapping discipline

The knowledge is subject-scoped (a practitioner's practices/artifacts); the host's
concerns are its **agent-meta surfaces** — `CLAUDE.md` instructions, hooks and
settings, CI workflows, and skills. Bridge the two yourself at run time: there is
no static subject allow-list and no fixed routing table. Ask of each candidate
practice: *which agent-meta surface here would it sharpen, and is that surface
weaker than the practice suggests it should be?* The gap between the two is the
proposal.

## Output

**At most one issue per channel per run** (zero per channel is fine), each picked
by the **one-proposal gate** run independently over that channel's candidates —
see [proposal-flow.md](proposal-flow.md) and
[ADR 0011](../../../docs/adr/0011-per-channel-proposal-caps.md). The base channels,
into the host repo's **own** tracker:

- **self-improvement** (`source:agent-research`) — one agent-meta improvement
  with a concrete before/after, citing the KB knowledge note that motivated it.
- **skill-audit** (`source:skill-audit`) — see the supply-side audit below.

The cross-repo channels (`skill-request`, `skill-promotion`, into
`dividedby/skills`) are described under their flows, below. Within every channel
the rule is unchanged: **never file a menu of options; make the call and file the
single best candidate, or skip.** Every filed body passes the **leak guard**
before filing. Zero across all channels is a fine run.

## Supply-side audit (Consumers with local skills)

If the host has **local skills** — skills in its own repo not published to
`dividedby/skills` — the loop audits them
([ADR 0010](../../../docs/adr/0010-consumers-audit-local-skills-supply-side.md)).
Enumerate each local skill and match it against the known skill universe: the
**published catalog** (read live from the fresh `dividedby/skills` clone the loop
makes to fetch this skill, [ADR 0008](../../../docs/adr/0008-consumers-fetch-the-skill-fresh-not-vendored.md))
**and** the **installed-skill snapshot** (`docs/agents/installed-skills.md`). One
scan, three verdicts:

- **Redundant** (matches an existing skill) → a `source:skill-audit` candidate
  in the host's own tracker: adopt the canonical skill, retire the local copy.
- **Promotable** (no match **and** clears general merit, [ADR 0001](../../../docs/adr/0001-buckets-cluster-by-user-intent.md))
  → a `skill-promotion` offer up to `dividedby/skills` (see
  [`skill-promotion-flow.md`](../../../docs/design/skill-promotion-flow.md)).
- **Repo-specific** (no match, not broadly useful) → keep, no-op.

This is the **mirror** of the demand-side already-do-this filter
([ADR 0009](../../../docs/adr/0009-skill-request-checks-existing-and-installed-skills.md)):
same matcher, pointed at what the host *already built* instead of what it
*wishes for*. A host with no local skills skips this entirely.

## Quality bar

- **One recommendation, not a menu.** Pick *the* best candidate. A forced finding
  is worse than none — if nothing clears the bar, skip and say why.
- **Concrete before/after.** Name the surface, quote what's there now (in prose,
  not as pasted code or path tokens that trip the guard), and state the exact
  change. Prescription proportional to diagnosis.
- **Generalized, leak-safe.** The tracker may be public and the host may be
  private; describe the need so it reads as broadly useful and carries no private
  content. The guard is a backstop, not a license to skip prose discipline.
- **Cite the source.** Reference the knowledge note(s) that motivated the proposal
  so a reviewer can trace the basis.

## Skills-repo specialization

The skills repo is a *special* consumer: its agent-meta *is* the published skills.
Beyond improving itself, here the skill also —

- **proposes skills on general merit** — a practice in the KB that warrants a
  net-new published skill (broadly useful per [ADR 0001](../../../docs/adr/0001-buckets-cluster-by-user-intent.md)),
  not just a refinement to an existing one; and
- **drains incoming `skill-request` issues** — open `skill-request` issues are
  cross-repo *demand*. Fold the best-supported one into a proposed skill. A request
  with more "+1 / also wanted by `<repo>`" corroboration carries more build
  priority — duplicate requests aggregate as demand, they are not noise
  ([ADR 0006](../../../docs/adr/0006-skill-request-demand-corroboration.md)). The
  inbound channel — issue contract, aggregation, and the per-Consumer write token —
  is designed in
  [`skill-request-flow.md`](../../../docs/design/skill-request-flow.md); this end
  only consumes what is already filed; and
- **owns the `skill-promotion` label and adopts offers** — incoming
  `skill-promotion` issues are cross-repo *supply*: a Consumer offering a local
  skill it already built (see
  [`skill-promotion-flow.md`](../../../docs/design/skill-promotion-flow.md)).
  Unlike demand, an offer is **already a concrete proposal with a reference
  implementation**, so it needs no folding into a candidate — the issue *is* the
  deliverable, reviewed and adopted by the human. The loop's only duty here is to
  **ensure the `skill-promotion` label exists** (the workflow does this
  idempotently, as it does for `skill-request`).

The self-improvement, general-merit, and skill-request-drain candidates are
*separate channels*, each capped at one issue per run by its own gate pass — not
one shared slot ([ADR 0011](../../../docs/adr/0011-per-channel-proposal-caps.md)).

## Invariants

- At most one issue **per channel** per run; the gate enforces each channel
  independently ([ADR 0011](../../../docs/adr/0011-per-channel-proposal-caps.md));
  zero per channel is acceptable.
- The skill writes **nothing** to the repo — no edits, no commits, no PRs. It
  proposes via an issue and stops.
- Every filed body passes the real leak guard; no private content reaches a public
  tracker.
- The mirror is read-only and derived; this skill never writes back to it or to
  `agent-research`.
