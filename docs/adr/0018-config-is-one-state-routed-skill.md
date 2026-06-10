# config/ is one state-routed skill; direction and domain are internal seams

The `config/` bucket originally held a deliberate 2×2 of four skills —
direction (`init-`/`audit-`) × domain (`-harness`/`-claude`) — with a
documented ordering (harness before instructions) and printed-pointer
handoffs between them. Issue [#184](https://github.com/dividedby/skills/issues/184)
(grilled from the Idea Inbox, #91) consolidated them.

Four pains motivated the change, all confirmed real by the maintainer:
discoverability (four slash commands plus knowing the 2×2 to pick one),
handoff friction (a full pass was a manually-chained two-step), boilerplate
duplication across four `SKILL.md`s ("earn the line", delegate-to-Explore,
propose-before-write), and a missing capability (no interview to fill gaps
the repo can't answer). The 2×2 was also awkward on the **common middle
case** — a repo with a `settings.json` but no `CLAUDE.md` (or vice versa)
needed `init` for the gaps and `audit` for what existed, forcing the user
to self-diagnose repo state.

## Decision

`config/` holds **one skill, `project-claude-config`, routed by repo
state**. Both former axes become internal seams the skill chooses per
concern, not user-facing skill boundaries:

1. **Direction (init/audit) → posture per concern.** The skill detects what
   exists; missing concerns get the additive scaffold posture
   (`scaffold-stubs.md`), present concerns get the subtractive audit posture
   (`audit-checklist.md`) — both in one pass.
2. **Domain (harness/instructions) → internal ordering.** The harness
   concern runs before the instructions concern, preserving the original
   rationale (a hook that enforces beats a line that asks), with no
   user-visible handoff.

The interview capability is added as a **gap-filler gated behind Explore**,
capped at the stub bar: ask only what the repo can't reveal, stop once
earn-the-line stubs plus a confirm/correct summary are possible.

To keep the single `SKILL.md` at principle level
([ADR 0002](./0002-design-skills-prescribe-at-principle-level.md)) despite
the larger surface, weight lives in supporting files: the shared
`CATALOG.md` is **broadened to both domains** (annoyance-filtered hook
entries + earn-the-line instruction entries, each fact-gated; proposals are
validated against the catalog's canonical doc anchors), and the two posture
files load lazily.

This supersedes the 2×2 as documented in the former `config/README.md`. It
does not conflict with [ADR 0001](./0001-buckets-cluster-by-user-intent.md)
— it applies the same lens one level down: the user intent is "get this
project's Claude config right"; direction and domain were implementation
seams, not intents.

## Rejected alternatives

- **One skill, user-selected init/audit modes (the raw idea).** Still makes
  the user self-diagnose repo state, and still splits the middle case
  across two invocations. State already determines the answer; asking is
  ceremony.
- **Two skills, merged on domain only (`init-project-config` /
  `audit-project-config`).** Keeps each skill tighter and the
  additive/subtractive bars separate, but retains the mode choice and fails
  the middle case the same way. The posture split survives inside the one
  skill as two supporting files, which captures the same separation without
  the user-facing boundary.
- **Keep the 2×2, add the interview to both init skills.** Fixes only one
  of the four pains; discoverability and handoff friction were the dominant
  ones.

## Consequences

- Four skills deleted; one added. `plugin.json`, top-level `README.md`, and
  `skills/config/README.md` updated. Installed-environment snapshots
  (`docs/agents/installed-skills.md`) refresh on their own cadence once the
  new skill is installed.
- [ADR 0013](./0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md)
  names the old skills; its body stays as a point-in-time record, with a
  one-line amendment note pointing here (the ADR 0004 precedent). Its
  carve-out now lives in `project-claude-config`'s `CATALOG.md` unchanged.
- Risk accepted: one skill now covers detect → scaffold → critique →
  interview across two domains. The mitigation is structural (thin routing
  `SKILL.md`; catalog and posture files carry the weight, loaded lazily) —
  if the surface still bloats, the recorded fallback is the two-skill
  domain-merged shape above.
