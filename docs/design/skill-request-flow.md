---
feature: skill-request-flow
status: accepted
---

# Design: the `skill-request` demand channel

How a Consumer repo that finds it needs a capability **no skill exists for** files
that demand into the `dividedby/skills` tracker, and how duplicate demand
aggregates across repos. This is the decentralized replacement for the retired
central gap-scanner: instead of one engine scanning the maintainer's repos for
gaps, each Consumer surfaces its *own* gap as a request. The substance was settled
in agent-research's cross-repo brief **§3**; this doc implements it and is the
contract a Consumer builds its filing step against.

The **aggregation rule** here — duplicates corroborate, they don't suppress — is
load-bearing and could look like a contradiction of agent-research ADR 0018. It is
not; see [ADR 0006](../adr/0006-skill-request-demand-corroboration.md).

## Who triggers it

The `apply-agent-research` loop, running in **any** Consumer. When the loop's
mapping step (KB practice → this repo's agent-meta) lands on a capability that
*should* exist as a published skill but does not, that is a `skill-request` — a
request **out to `dividedby/skills`**, distinct from the at-most-one
`source:agent-research` issue the loop files **into its own** tracker.

## The issue contract

A `skill-request` issue lives in `dividedby/skills`, carries the `skill-request`
label, and its body states three things:

- **Capability wanted** — what the skill would do, in generalized terms (the
  same leak-safe discipline as `source:agent-research`: no host-private content,
  the tracker is public).
- **Motivating knowledge** — the `agent-research` knowledge note(s) that surfaced
  the need, so the maintainer can trace the basis.
- **Requesting repo** — which Consumer felt the gap.

It embeds a stable **capability key** so later requests can find it:

    <!-- capability: <kebab-case-slug> -->

The slug names the *wanted capability*, not the prose (e.g.
`capability: parallel-subagent-fan-out`). The same gap from a different repo must
produce the same slug — that is what makes aggregation work.

> **Same marker, opposite action.** The capability key mirrors the `dedup-key`
> marker in [`apply-agent-research`'s proposal-flow](../../skills/meta/apply-agent-research/proposal-flow.md),
> but the semantics **invert**: there a matching key *suppresses* a re-file (one
> repo's own one-per-run cap); here a matching key *triggers a +1* (cross-repo
> demand corroboration). Don't reuse `proposal_gate` for this — it is the wrong
> rule (see ADR 0006).

## Aggregation: duplicates corroborate

Before filing, the Consumer lists open `skill-request` issues in `dividedby/skills`
and matches on the capability key:

- **No match** → open a new issue with the contract above.
- **Match exists** → **do not** open a second issue. Post a comment:
  `+1 — also wanted by <repo>` plus its own motivating knowledge. N such comments
  on one issue is the demand signal.

The **skills-repo draining end** (the `apply-agent-research` specialization, built
in the skill) reads these open `skill-request`s and their accumulated "+1" tally as
input to *which* skill to propose next: more corroborating repos raises build
priority. Demand sets build order; it does not by itself justify a skill —
usefulness of a *built* skill is still settled by adoption (no adoption tracker).

## Cross-repo write token (per Consumer)

The default `GITHUB_TOKEN` is own-repo scoped and **will 403** writing into
`dividedby/skills`. Each Consumer provisions its own credential:

- **Mechanism: a fine-grained PAT**, least-privilege:
  - **Repository access:** only `dividedby/skills` (not "all repositories").
  - **Permissions:** `Issues: Read and write` (file the issue, read existing ones
    to aggregate, post the +1 comment) and the implied `Metadata: Read`. Nothing
    else.
- **Storage:** as a per-Consumer Actions secret (e.g. `SKILLS_TRACKER_TOKEN`),
  referenced only by that Consumer's `apply-agent-research` workflow.
- **Scoping note — the label must pre-exist.** Creating labels is not guaranteed
  under fine-grained `Issues: write`, so `dividedby/skills` **owns** the
  `skill-request` label (created here, idempotently re-ensured by the draining
  workflow). Consumers only *apply* the existing label; they never create it.
- **Rotation:** fine-grained PATs expire — set a finite expiry and rotate by
  regenerating the token and updating each Consumer's secret. Because the token is
  single-repo + issues-only, a leak's blast radius is "file/Comment issues on the
  public skills tracker," not repo write.
- **Fork-PR safety:** Actions does not pass secrets to workflows triggered by
  fork PRs, so the token is exposed only on the maintainer's own scheduled /
  dispatched runs.

If the Consumer count grows enough that manual PAT rotation becomes a burden, the
scale-up is a **GitHub App** with `issues:write` on `dividedby/skills` (short-lived
installation tokens, central revocation). Not built now — a fine-grained PAT is
right for a single-maintainer, few-repo setup.

## What lives where

- **In `dividedby/skills` (this repo):** the `skill-request` label (owned here),
  this contract, [ADR 0006](../adr/0006-skill-request-demand-corroboration.md), and
  the **draining** end (the `apply-agent-research` skill's specialization, already
  built).
- **In each Consumer repo:** the **filing** step inside its own
  `apply-agent-research` workflow (list-or-file-or-+1 against `dividedby/skills`
  using `SKILLS_TRACKER_TOKEN`), plus the secret itself. Built per Consumer as
  Consumers are onboarded — none exist yet, so there is no filing code in this repo.

## Invariants

- Duplicate requests **aggregate** (+1 comment), never dedup-suppress (ADR 0006).
- The cross-repo credential is a least-privilege, single-repo, issues-only token;
  never the default `GITHUB_TOKEN`.
- `dividedby/skills` owns the `skill-request` label; Consumers apply, never create.
- Demand corroboration sets build *priority* only; adoption still settles whether a
  built skill earns its place.
