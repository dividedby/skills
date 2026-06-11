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

### Installed skills

Capabilities installed in the maintainer's global environment (`~/.claude/`) are
available in every session even when not files under this repo's `skills/`. A
committed snapshot lives at `docs/agents/installed-skills.md` so remote loops can
read it. See `docs/agents/installed-skills.md`.

### Skill editorial intent

Skills in this repo prescribe at the principle level; code examples are illustrative sketches, not literal rules. See [`docs/adr/0002-design-skills-prescribe-at-principle-level.md`](./docs/adr/0002-design-skills-prescribe-at-principle-level.md).

### Intake convention

When I say **"file an idea"** or **"file an issue"** (unqualified), append an
**enriched row** to this repo's [**Idea Inbox**](./CONTEXT.md) issue (label
`idea-inbox`, one per repo): the raw idea **plus the ambient context/links
available right now** — the source file/issue/PR that prompted it and a sentence
of why — as an unchecked item at the TOP of `## Ideas`. Do not grill or scope it
yet; that happens at drain. The capture and drain protocol lives once in
[`docs/agents/idea-inbox.md`](./docs/agents/idea-inbox.md) (the issue body is
human-facing and carries no operating instructions — ADR 0024).

When I say **"file a *tracked* issue"** — or hand you a **plainly-scoped bug** —
skip the Inbox and file a `needs-triage` issue directly via `gh`.

Both paths still register in the [**Roadmap**](./CONTEXT.md), the execution
source of record: every filing registers there, but **not** every filing funnels
through the Inbox (ADR [0021](./docs/adr/0021-idea-inbox-is-the-unstructured-intake-everything-registers-in-the-roadmap.md)). The SessionStart drift nudge flags any open
issue missing from the census, so drained and directly-filed issues both get
slotted by `/roadmap` with no extra step. Intake is this convention, not a skill.
