# `repair_json` is duplicated under a CI drift guard

## Context

[#369](https://github.com/dividedby/skills/pull/369) fixed the `gate`
subcommand's malformed-JSON brittleness: consolidated-JSON with a trailing comma
or a lone control character in a string field caused the entire gate run to drop.
The fix applied the same recovery doctrine established in
[ADR 0025](0025-publish-seam-recovers-malformed-output-loudly-before-failing.md)
to the gate's parse seam, reusing the `_repair_json` heuristic from
`harness/cli.py`.

The maintainer asked for one shared import to avoid drift. The candidate
approaches all collide with a hard constraint: the skill must stay self-contained.

- It is `cp -R`'d into `~/.claude/skills/` at Consumer setup (consumer-setup.md
  step 1) and installable standalone via `pnpm dlx skills add` (README).
- Anything outside the skill folder is not guaranteed present at its runtime
  ([ADR 0008](0008-consumers-fetch-the-skill-fresh-not-vendored.md)).
- The harness and the skill are independently fetched
  ([ADR 0014](0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md));
  their on-disk paths are not guaranteed to coincide.

## Decision

Keep two copies — canonical `_repair_json` in `harness/cli.py`, an authorized
verbatim copy `repair_json` in the skill's
`lib/json_repair.py` — and enforce byte-identity with a CI drift guard
(`harness/tests/test_repair_json_drift.py`) triggered on edits to either tree.

The guard strips the `def` line (names differ: `_repair_json` vs `repair_json`)
and the docstring (text may differ), then asserts the executable body below is
byte-identical. A one-sided edit makes the guard fail before the copies can
diverge in behaviour. Silent drift becomes impossible; the manual sync chore
becomes an enforced invariant.

This is consistent with [ADR 0025](0025-publish-seam-recovers-malformed-output-loudly-before-failing.md)'s
loud-beats-lossy / detect-don't-prevent doctrine: the duplication is visible,
bounded (~50 lines), and machine-checked.

## Consequences

- ~50 lines duplicated but cannot silently diverge.
- A change to the repair heuristic must touch both copies or CI fails; the error
  message names both file paths and the canonical source.
- `harness-tests.yml` `paths:` filter now includes the skill's copy so a
  skill-only edit also fires the drift guard.

## Rejected alternatives

**(a) Shared module in `harness/`.** The skill imports from `harness/cli.py` at
gate runtime. Breaks standalone skill install: harness is absent when the skill
travels to a Consumer without the repo clone (ADR 0008, ADR 0014). Rejected.

**(b) Harness imports from the skill.** Inverts the layering: a generic lower
rail depending on one specific skill. Also breaks `harness-tests.yml`'s
`harness/**` path isolation. Rejected.

**(c) Skill imports harness at gate runtime via `$SKILLS_SRC/harness`.** The
proposal-loop always has the full `dividedby/skills` clone on disk, so every
real `gate` run technically has access. But: it spends ADR 0008 self-containment
on ~50 lines; it couples the skill to a private harness internal and its exact
file layout; and it still needs a fallback copy for the skill's isolated
guard-test gate and standalone load. A bad exchange rate; the saved duplicate
shows up again as a conditional fallback. Rejected.
