Skills are organized into bucket folders under skills/:

    engineering/ — daily code work
    config/      — setting up and auditing a project's Claude config (instruction files + settings/hooks harness)
    meta/        — applying external agent-research knowledge to improve this repo's own agent-meta

Each skill is registered in `.claude-plugin/plugin.json` (`skills[]`) and linked from the top-level `README.md` with a one-line description — enforced by the `check-skill-registration` Stop hook.

A bucket's own `README.md` is **not** required by default. Add one only when either: (a) the repo has ≥3 buckets and the top-level README is getting long, or (b) a single bucket holds ≥3 skills and a localized index aids navigation.

## Conventions

Cross-cutting rules that multiple skills follow. Not invokable — read by
skills during their work. See [`CONTEXT.md`](./CONTEXT.md) for vocabulary.

### Issue tracker

Issues live in GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Skill editorial intent

Skills in this repo prescribe at the principle level; code examples are illustrative sketches, not literal rules. See [`docs/adr/0002-design-skills-prescribe-at-principle-level.md`](./docs/adr/0002-design-skills-prescribe-at-principle-level.md).
