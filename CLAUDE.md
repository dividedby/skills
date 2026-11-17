Skills are organized into bucket folders under skills/:

    engineering/ — daily code work

Each skill is registered in `.claude-plugin/plugin.json` (`skills[]`) and linked from the top-level `README.md` with a one-line description — enforced by the `check-skill-registration` Stop hook.

A bucket's own `README.md` is **not** required by default. Add one only when either: (a) the repo has ≥3 buckets and the top-level README is getting long, or (b) a single bucket holds ≥3 skills and a localized index aids navigation.

## Checks

- `pnpm format:check` (Prettier; `pnpm format` fixes) and `ruff format --check .` — both run in CI (`.github/workflows/format.yml`).
- Hook and script self-tests: `python3 .claude/hooks/check-skill-registration.test.py`, `python3 .claude/hooks/destructive-git-guard.test.py`, `python3 docs/agents/labels.test.py`. Plain `python3`, no pytest needed.

## Conventions

Cross-cutting rules that multiple skills follow. The rules themselves aren't
invokable — skills read them during their work (the Ideas bullet points at the
`idea-intake` skill, which is). See [`CONTEXT.md`](./CONTEXT.md) for vocabulary.

- **Issue tracker, labels, domain docs:** GitHub Issues via `gh` ([`docs/agents/issue-tracker.md`](./docs/agents/issue-tracker.md)); triage labels `needs-triage`, `ready-for-agent`, `ready-for-human`, `blocked`, `wontfix` ([`docs/agents/labels.md`](./docs/agents/labels.md)); single-context `CONTEXT.md` + `docs/adr/` ([`docs/agents/domain.md`](./docs/agents/domain.md)).
- **Ideas:** Idea Inbox is issue #91 (label `idea-inbox`); protocol in [`docs/agents/idea-inbox.md`](./docs/agents/idea-inbox.md).
- **Skill editorial intent:** skills prescribe at the principle level; code examples are illustrative sketches, not literal rules. See [`docs/adr/0002-design-skills-prescribe-at-principle-level.md`](./docs/adr/0002-design-skills-prescribe-at-principle-level.md).
- **Invocation:** skills here are user-invoked orchestrators by default — each `SKILL.md` carries `disable-model-invocation: true`, so its description doesn't load into every session's context. A skill that must fire on a phrase (`idea-intake`) omits the flag.
- **Skill authoring:** composition patterns and worked editorial-judgement examples live in [`docs/agents/skill-authoring.md`](./docs/agents/skill-authoring.md). Read it when authoring a new skill or deciding whether to add a code example to an existing skill. Markdown style: [`CODING_STANDARDS.md`](./CODING_STANDARDS.md).
- **Changelog:** notable changes land in [`CHANGELOG.md`](./CHANGELOG.md) (Keep a Changelog; hand-maintained per [ADR 0034](./docs/adr/0034-fleet-changelogs-are-hand-maintained-and-llm-evaluated.md)). It tracks the published surface: the skills catalog (and, through 2.0.0, the `harness/` Python). Entry rubric: [`docs/agents/changelog-guideline.md`](./docs/agents/changelog-guideline.md).

## Code style

Formatting uses each tool's standard defaults; don't add style options or format by hand. Files format on edit through the post-edit hook. Check with `pnpm format:check`.
