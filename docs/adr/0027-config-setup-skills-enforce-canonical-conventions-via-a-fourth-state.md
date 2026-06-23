# Config-setup skills enforce canonical conventions via a fourth state

`setup-dividedby-skills` (and the config-setup skills generally) resolved every
convention check into one of three outcomes: **create**, **update**, or **skip**.
A *known* non-canonical form could resolve to `skip` and silently persist.

## Context

The label-convention doc drifted into four shapes across active repos (canonical
single `docs/agents/triage-labels.md`; a two-file `labels.md` + `triage-labels.md`
split; a short-form/pointer `triage-labels.md`; a `labels.md`-only repo). When
`setup-dividedby-skills` last ran on a split repo, its `skip`-dominant posture
tolerated the deviation; a human had to notice and request consolidation, then it
was propagated by hand across ~9 repos.

The skills were **detect-and-offer** with a skip bias rather than **enforcing**
the canonical form. For a surface that is *pure convention with no judgment call*
(file name, single-vs-split, full-vs-pointer), tolerating a known deviation is a
bug, not flexibility. This does not conflict with [ADR 0002](./0002-design-skills-prescribe-at-principle-level.md):
that governs how a skill *phrases its guidance*, not whether a skill enforces a
mechanical file-layout convention.

The fix must not weaken the propose-only safety posture: bringing a repo to
canonical means **destructive** edits (delete a stray `labels.md` after
retargeting refs; rewrite a short-form `triage-labels.md` to the full
convention), and those must not happen silently by default.

## Decision

Add a fourth outcome and an opt-in mode:

- **`must-fix` state.** A *known* non-canonical convention form can no longer
  resolve to `skip`. It resolves to `must-fix`: the skill surfaces the exact
  destructive diff (what it will delete/rewrite and why) and **requires
  confirmation** before applying it. The propose-only default is preserved —
  nothing destructive happens without an explicit yes.
- **`force-canonical` mode.** An explicit maintainer opt-in that applies all
  `must-fix` items with **no per-deviation prompt**. Justified only because the
  fixes are pure convention with zero judgment. Its scope is **convention-only**:
  anything requiring judgment still prompts, even in force mode.

`must-fix` is distinct from `update`: `update` is a routine reconciliation the
skill may do under its normal posture; `must-fix` is a known-bad form whose fix
is destructive and therefore gated on confirm (or `force-canonical`).

## Consequences

- The three-state model becomes four: **create / update / skip / must-fix**. A
  `skip` now means "already canonical," never "non-canonical but left alone."
- Maintainers get a one-shot fleet path (`force-canonical`) for convention-only
  drift, without re-introducing silent destructive edits as the default.
- Skills must classify each convention as *convention-only* (eligible for
  `force-canonical`) or *judgment-bearing* (always prompts). New conventions
  declare which they are.
- Pairs with the drift-detection rule in [ADR 0023](./0023-setup-dividedby-skills-vs-project-claude-config-seam.md):
  `project-claude-config` flags label-doc drift and hands off; `setup-dividedby-skills`
  is what actually resolves it via `must-fix` / `force-canonical`.
