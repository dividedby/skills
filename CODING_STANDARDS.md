# Coding Standards

Standards for the published surface of this repo: **markdown skills** (the
`skills/` tree). Read this alongside
[`CLAUDE.md`](./CLAUDE.md) and
[ADR 0002](./docs/adr/0002-design-skills-prescribe-at-principle-level.md), which
this document references rather than restates.

**Seam:** this file = code/authoring norms; [`CLAUDE.md`](./CLAUDE.md) = agent
behavior and Conventions; [`docs/adr/`](./docs/adr/) = binding design decisions.
The three are complementary; this doc defers to the others rather than
duplicating them.

---

## Markdown skills (`skills/`)

### Frontmatter

Every `SKILL.md` opens with a YAML frontmatter block:

```yaml
---
name: <slug>
disable-model-invocation: true
description: >
  One-sentence description (loaded by the plugin host).
---
```

`disable-model-invocation: true` is the **default** for all skills in this repo
— it keeps the skill's description out of every session's ambient context (see
[CLAUDE.md § Skill editorial intent](./CLAUDE.md)). Omit the flag only when a
skill is deliberately model-fired on a signal (current exception: `flow-pr`,
which the model invokes on done+green).

### Prescribe at the principle level

Skills prescribe **principles**, not stack-specific idioms. Code examples inside
a skill are illustrative sketches of a principle's shape, not rules to follow
literally. See [ADR 0002](./docs/adr/0002-design-skills-prescribe-at-principle-level.md)
for the rationale and the worked counter-example.

Concretely: match the density of the surrounding section. A deliberately terse
block stays terse; adding a code snippet to one item in an otherwise
snippet-free block implies the snippet IS the rule — avoid this unless the
example genuinely unlocks value prose cannot.

### Registration

Every skill must be:

1. Listed under `skills[]` in `.claude-plugin/plugin.json`.
2. Linked from the top-level `README.md` with a one-line description.

The `check-skill-registration` Stop hook enforces this; it runs automatically
and will block unregistered skills.

### Structure

- Use ATX headings (`#`, `##`, `###`).
- Lead with the frontmatter block; follow with a `# Title` heading, then the
  skill body.
- Reference other docs by relative path from the repo root. Prefer linking over
  re-stating content that already lives in `CLAUDE.md`, `CONTEXT.md`, or an ADR.
- Defers / dependencies go in a short `Defers:` block near the top, not buried.
