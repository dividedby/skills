# config/

Skills for setting up and auditing a project's Claude configuration. Two
domains, each with an additive (`init-`) and a subtractive (`audit-`) skill:

- **Instruction files** — `CLAUDE.md` / `AGENTS.md`.
- **Harness** — `.claude/settings.json` (hooks, `env`, deny-only permissions,
  light plugins).

All four are manual/slash invocation only (`disable-model-invocation: true`)
and share one bar: **every line costs context or runs every session, so it
must earn its place.** Nothing here restates or weakens the global
`~/.claude/` config; it adds only project-specific value.

## The four skills

| Skill | Domain | Direction |
|---|---|---|
| `init-project-harness` | harness | additive — scaffold settings/hooks when absent |
| `audit-project-harness` | harness | subtractive — critique existing settings/hooks |
| `init-project-claude` | instructions | additive — scaffold missing instruction files |
| `audit-project-claude` | instructions | subtractive — critique existing instruction files |

Each `init` skill stops and points at its `audit` counterpart if the files
already exist, and vice versa.

## Ordering: harness first

Run the **harness** pass before the **instructions** pass. A hook that
enforces something automatically (deterministic, zero context cost) beats a
`CLAUDE.md` line asking the agent to remember it — so settling the harness
first lets the instructions pass *cut* anything a hook now enforces.

```
/init-project-harness   →  /init-project-claude     (greenfield)
/audit-project-harness  →  /audit-project-claude    (existing repo)
```

Skills hand off with a printed pointer, never by auto-invoking. Genuine
judgment calls are surfaced for an optional `/grill-me` pass.

## Shared catalog

The two harness skills draw recommendations from a single fact-gated catalog
at [`init-project-harness/CATALOG.md`](./init-project-harness/CATALOG.md):
each entry has a trigger, value, annoyance cost, and a canonical doc anchor.
Proposals are validated against live Claude Code docs (via WebFetch against the
catalog's canonical doc anchors) before approval, and settings writes route
through the `update-config` skill.
