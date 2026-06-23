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

Default vocabulary: `needs-triage`, `ready-for-agent`, `ready-for-human`, `blocked`, `wontfix`. See `docs/agents/labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Installed skills

Capabilities installed in the maintainer's global environment (`~/.claude/`) are
available in every session even when not files under this repo's `skills/`. A
committed snapshot lives at `docs/agents/installed-skills.md` so remote loops can
read it. See `docs/agents/installed-skills.md`.

### Workflow authoring

Adding or re-cadencing a scheduled `claude -p` workflow (a proposal loop here or in any consumer): pin `--model` to an exact ID, carry a `--max-budget-usd` backstop, emit `total_cost_usd` via `harness/cli.py digest`, onboard into the cross-repo `COST_SURFACE`, and self-stagger the cron by hash. See `docs/agents/workflow-authoring.md`. Binding decisions: ADR 0019 (budget/cap + cadence), ADR 0014 (fetched-fresh envelope).

### Skill editorial intent

Skills in this repo prescribe at the principle level; code examples are illustrative sketches, not literal rules. See [`docs/adr/0002-design-skills-prescribe-at-principle-level.md`](./docs/adr/0002-design-skills-prescribe-at-principle-level.md).

Skills here are user-invoked orchestrators by default — each `SKILL.md` carries `disable-model-invocation: true`, so its description doesn't load into every session's context. Exception: a skill deliberately model-fired on a signal (e.g. `flow-pr` on done+green) omits the flag by design.

### Changelog

Notable changes land in the top-level [`CHANGELOG.md`](./CHANGELOG.md) (Keep a Changelog format) — the human-readable record the version-bump / roll-up step updates. It tracks the two published surfaces: the skills catalog and `harness/`.

### Coding standards

Authoring and code style for markdown skills and `harness/` Python. See [`CODING_STANDARDS.md`](./CODING_STANDARDS.md).

<important if="filing an issue or idea">

### Intake convention

- **"file an idea"** / unqualified **"file an issue"** → append an enriched row (the raw idea **plus the ambient context/links available now**) to the top of the [Idea Inbox](https://github.com/dividedby/skills/issues/91) (`idea-inbox`, one per repo); don't scope it yet.
- **"file a *tracked* issue"** or a plainly-scoped bug → skip the Inbox, file a `needs-triage` issue directly via `gh`.

Capture/drain protocol: [`docs/agents/idea-inbox.md`](./docs/agents/idea-inbox.md).

</important>
