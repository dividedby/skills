# Retire unused catalog skills and fold flow-pr into branching-flow

> **Status: Accepted** — maintainer decision (2026-10-12), taken after [ADR 0039](./0039-retire-remaining-proposal-loops-and-loop-serving-skills.md) retired the loops and left ten skills registered.

## Context

[ADR 0039](./0039-retire-remaining-proposal-loops-and-loop-serving-skills.md)
removed the loops, `harness/` and the skills that served them. Ten skills remained
in the plugin. On review, eight of them were not earning their upkeep:

- `doc-it`, `autonomous-loop`, `software-design`, `frontend-design` and
  `write-well` (engineering), and `project-claude-config` and `triage` (config):
  unused by the maintainer, or superseded by an upstream skill or a plain
  conversation.
- `flow-pr`: the only skill whose content is better held as part of the
  maintainer's global branching and merge flow than as a published skill. Its
  review gate, autonomy triggers, PR body layout and promotion rules are
  maintainer-specific and are model-fired on a signal, the one exception to the
  `disable-model-invocation` default.

`council` and `repo-audit` are still used and stay.

## Decision

**Retire all eight skills from the published catalog.**

- Delete `doc-it`, `autonomous-loop` (with `EVALUATOR-GATE.md`, `FIREWALL.md` and
  `RUNNING-AFK.md`), `software-design`, `frontend-design`, `write-well`,
  `project-claude-config`, `triage` and `flow-pr` (with `merge-mechanics.md`), and
  remove them from `.claude-plugin/plugin.json` and the top-level `README.md`.
- `flow-pr`'s content now lives in `dividedby/claude-config`: the PR flow section of
  `branching-flow.md` plus a `/flow-pr` command. It is not published here.
- Make `council`'s false-positive exclusion list canonical for the published
  plugin. The maintainer keeps a hand-synced copy in their own
  `~/.claude/branching-flow.md` review gate, which is not part of this repo.
- Delete `skills/engineering/README.md` (two skills remain, under the
  three-skill threshold in `CLAUDE.md`) and the `config/` bucket.
- Move `skills/config/labels.test.py` to `docs/agents/labels.test.py`, beside the
  doc it tests, and point the CI gate's test glob at `docs/agents/*.test.py`.
- Mark the ADRs whose subject is wholly retired as superseded by this ADR: 0005,
  0018, 0022, 0033 and 0035; 0023 gains a second note because both sides of its
  seam are now gone. Their bodies are not rewritten.

**Unaffected:** `council`, `repo-audit`, the Idea Inbox convention, the
`check-skill-registration` Stop hook, and the soft-dependency posture toward
`mattpocock/skills` and `anthropics/claude-plugins-official`
([ADR 0024](./0024-lean-on-upstream-skills-soft-depend-over-reinvent.md)).

ADRs that name a retired skill but whose decision stands (0002, 0003, 0019, 0020, 0024,
0028, 0036) are left unmarked. ADR 0013 gets a "superseded in part" note because it names
`project-claude-config`'s deleted `CATALOG.md` as its carve-out's home. ADR 0012 is already
superseded by 0033, which this ADR supersedes, so the chain stays reachable.

## Consequences

- The published catalog shrinks to two skills and the changelog rolls to 3.0.0.
  The removals are flagged **Breaking**.
- Consumers who installed any of the eight skills must remove them. `/flow-pr` for
  the maintainer resolves to the `claude-config` command once the installed skill
  is removed by hand.
- The `config/` bucket and `skills/engineering/README.md` no longer exist.
- Rejection records under `.out-of-scope/`, design docs under `docs/design/`, ADR
  bodies and older changelog entries that name the retired skills are left as
  history.
- Reinstating any of the eight would need a new decision; nothing is kept beyond
  git history.
