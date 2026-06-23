# Coding Standards

Standards for the two published surfaces of this repo: **markdown skills** (the
`skills/` tree) and **harness Python** (`harness/`). Read this alongside
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

---

## Harness Python (`harness/`)

### Style

- Python 3. Type annotations on public functions; omit for purely internal
  one-liners where the type is obvious from context.
- Follow the project convention seen in `cli.py`: module-level docstring
  explaining why this module exists, then public helpers, then private helpers
  (`_` prefix), then subcommand handlers, then `main`.
- Comments explain *why*, not *what*. Comment non-obvious decisions; omit
  narration.
- Line length: stay within ~90 characters (the codebase does not enforce a hard
  formatter, but existing code is consistently within this range).

### Docstrings

Public functions carry a docstring. Convention (from `cli.py`):

- First line: one sentence describing what the function returns or does.
- Body (when needed): contract, edge cases, recovery hierarchy.
- No reStructuredText field markers (`Args:`, `Returns:`) — use prose.

Private helpers (`_` prefix) carry a docstring only when the logic is
non-obvious.

### Error handling

- Distinguish *loud* failures from *lossy* silent ones. Prefer loud: raise
  `ValueError` with a clear message and let callers decide whether to degrade
  or abort (the "loud beats lossy" principle from `#117`).
- I/O subcommand handlers (the thin transport layer) catch `ValueError` and
  return exit code 1; they never swallow errors silently.
- Best-effort operations (e.g. `_ensure_label`) use `subprocess.run` without
  `check=True` and document why silence is acceptable.

### Module boundaries

- **Pure helpers** (no I/O, deterministic): isolated at the top of the module,
  unit-tested directly. These hold the load-bearing logic.
- **Subcommand handlers**: thin wrappers that open files, invoke `gh`, and call
  the pure helpers. They are not unit-tested in isolation; the pure helpers
  beneath them are.
- The harness is invoked by file path (`python3 <clone>/harness/cli.py`), not
  imported. Keep the public API surface narrow.

### Tests

- Test files live in `harness/tests/`, named `test_<subject>.py`.
- Use `unittest.TestCase`; no pytest plugins.
- Bootstrap `sys.path` at the top of each test file so `import cli` resolves
  without installation.
- Mock `subprocess` / env at the handler boundary; never let tests call `gh` or
  touch the filesystem beyond `tempfile`.
- The "loud beats lossy" contract is what deserves a test: missing/malformed
  output must fail loudly; the transport layer must not call `gh` on a parse
  failure.

### Stdlib-only

The harness uses the Python standard library only — no third-party dependencies.
This keeps the fetch-fresh install path simple (no `pip install` step in the
workflow envelope). New helpers must stay within this constraint.
