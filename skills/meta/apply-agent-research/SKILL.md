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

## The mapping discipline

The knowledge is subject-scoped (a practitioner's practices/artifacts); the host's
concerns are its **agent-meta surfaces** — `CLAUDE.md` instructions, hooks and
settings, CI workflows, and skills. Bridge the two yourself at run time: there is
no static subject allow-list and no fixed routing table. Ask of each candidate
practice: *which agent-meta surface here would it sharpen, and is that surface
weaker than the practice suggests it should be?* The gap between the two is the
proposal.

## Output

At most one issue per run (zero is fine), labeled `source:agent-research`, into the
host repo's **own** tracker. The body proposes one agent-meta improvement with a
concrete before/after and cites the knowledge that motivated it. It must pass the
**leak guard** and the **one-proposal gate** mechanically — see
[proposal-flow.md](proposal-flow.md). Never file a menu of options; make the call
and file the single best candidate, or skip.

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
  cross-repo *demand*. Fold the best-supported one into a proposed skill. Treat
  duplicate requests as corroborating demand, not noise. (The inbound
  `skill-request` channel itself is designed separately; this end only consumes
  what is already filed.)

These are *additional candidate sources* feeding the same one-proposal-per-run
gate — not extra issues. Still at most one issue per run.

## Invariants

- At most one issue per run; the gate enforces it; zero is acceptable.
- The skill writes **nothing** to the repo — no edits, no commits, no PRs. It
  proposes via an issue and stops.
- Every filed body passes the real leak guard; no private content reaches a public
  tracker.
- The mirror is read-only and derived; this skill never writes back to it or to
  `agent-research`.
