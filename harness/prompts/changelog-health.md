# Weekly changelog-health pass

You are running unattended in GitHub Actions. No user is watching. Do not ask
questions — make the call yourself.

You **do not file anything yourself.** Your entire output is a single `<output>`
block at the very end of your response (schema below), plus — only when
proposing — one `<body>` block holding the raw advisory. A deterministic
workflow step parses those blocks and publishes the issue — this is what keeps
the single-open-advisory-per-repo invariant in code rather than trusting the
prompt. Do **not** run `gh issue create`; if you do, you will create a
duplicate.

## What this loop does

It reads each enrolled repo's `CHANGELOG.md` against its recent `git log`, and
against the grading checklist in `docs/agents/changelog-guideline.md`. When it
finds notable changes that shipped but are not reflected in `## [Unreleased]`,
or finds rubric violations, it proposes advisory `## [Unreleased]` lines and/or
cites the offending rule numbers. The advisory is a human nudge, not a gate:
the maintainer hand-applies (or ignores) the suggestion.

## Tool-use constraint

Your only shell commands are the read-only git set: `git log`, `git diff`,
`git show`, `git ls-files`, `git status`. There is no `gh` in your allowlist —
you file nothing yourself (see Output contract). Command pipelines (a
`grep`/`sort`/`comm` chain) and other batch idioms (`for`/`while` loops,
`bash -c`) are matched as one opaque string and denied — use the `Grep` tool
and reason over its results instead of piping shell commands together.
Everything else is `Read`, `Grep`, `Glob`.

## Task

One repo per job run (the matrix fans out at the workflow level). The repo
under evaluation is checked out at your current working directory.

For each repo:

### 1. Read the rubric

Read the grading rubric from the absolute path given in your task message
(`$SKILLS_DIR/docs/agents/changelog-guideline.md`). This is your grading
criteria. Each of the eight rows in the **Grading checklist** table is a
numbered rule you can cite in the advisory.

### 2. Read the changelog and git log

Your current working directory IS the target repo.

- Read `CHANGELOG.md` in full.
- Identify the most recent dated `## [x.y.z] - YYYY-MM-DD` section (or, if
  none exists, treat the entire history as post-baseline). Everything between
  the top of the file and that section is the current `## [Unreleased]` content.
- Run `git log --stat` from the last dated section's merge date to HEAD to
  discover commits that merged after the last versioned entry:

  ```
  git log --oneline --stat <last-dated-commit-ish>..HEAD
  ```

  For a `[YYYY-MM-DD]` header, pick a reasonable approximation of the boundary
  commit via `git log --after="YYYY-MM-DD" --oneline`.

- For any commit that looks notable (new feature, behavior change, bug fix,
  removal, deprecation, or security fix), check whether a corresponding entry
  already exists in `## [Unreleased]`. Be generous: if an entry covers the
  commit semantically, it counts. Only flag genuinely missing coverage.
- Apply the eight grading-checklist rules to the current `## [Unreleased]`
  content. Cite rule numbers when flagging violations.

### 3. Decide

- If the changelog is current (no missing notable entries AND no rule
  violations) → emit `{"status":"skipped","reason":"changelog current"}`.
- If there is at least one missing entry or one violation → proceed to step 4.

### 4. Draft the advisory

Write a single advisory body (the `<body>` block) containing:

**a. Proposed `## [Unreleased]` lines** (if any notable changes are missing):
  - Sort entries into the six Keep a Changelog 2.0.0 categories:
    Added / Changed / Deprecated / Removed / Fixed / Security.
  - Write each entry in consumer voice — what changed for the user of the
    surface, in plain language. One line per notable change. Include PR/commit
    refs as trailing `(#N)` or `(sha)` references.
  - Mark any backward-incompatible change with `**Breaking:**` prefix (rule 5).
  - State explicitly that this is a proposal for the maintainer to hand-apply;
    this loop never edits `CHANGELOG.md`.

**b. Rubric violations** (if any):
  - For each violation, cite the rule number from the grading checklist and
    quote the offending text.

The advisory must be clearly marked as a proposal/nudge, not a gate.

## Output contract

End your response with a small machine-parsed `<output>` JSON block, **followed
by** — only when proposing — one `<body>` block holding the raw advisory.

The split is deliberate and load-bearing: the `<output>` JSON carries only
**short, single-line** fields, so it stays valid JSON. The advisory body — long
prose with embedded markdown — goes in the `<body>` block as **raw markdown**,
where it needs **no JSON escaping**. Do **not** put the body inside the JSON.

Emit valid JSON in `<output>`, copy the field names exactly, and add no fields
beyond those listed. It has one of two shapes.

Advisory to propose — emit the `<output>` block, then the `<body>` block, in
that order, as the very last things you write:

```
<output>
{
  "status": "proposed",
  "title": "Changelog drift: N unrecorded change(s)",
  "oneLineSummary": "One-line description of what drifted."
}
</output>
<body>
The full advisory body as raw markdown. No escaping — write it exactly as it
should appear in the filed issue. Do not include the <body> / </body> markers
in the prose itself.
</body>
```

Nothing to flag — emit only the `<output>` block, no `<body>`:

```
<output>
{
  "status": "skipped",
  "reason": "changelog current"
}
</output>
```

Field rules:

- `status` — `"proposed"` or `"skipped"`. Required.
- `title` — required when proposed; ≤256 chars; keep it on one line. Use the
  form `Changelog drift: N unrecorded change(s)` (or a rubric-only variant
  like `Changelog health: 2 rubric violations` when drift is rubric-only).
- `oneLineSummary` — required when proposed; one line.
- `reason` — required when skipped.
- The `<body>` block — present when proposed, omitted when skipped; raw
  markdown, no JSON escaping.

## Rules

- **Read-only. You file nothing.** No commits, no edits, no `gh issue create`,
  no `gh issue comment`. The workflow publishes the advisory (and applies the
  `source:changelog-health` label) from your `<output>` + `<body>` blocks.
  The workflow's publish step also handles dedup (single-open-advisory) via
  `--dedup-open` — you do not need to check for open advisories yourself.
- **Flag, never rewrite.** The advisory proposes entries the maintainer
  hand-applies. It never modifies `CHANGELOG.md` or any other file.
- **No questions.** There is no user.
- End every run with exactly one `<output>` block (plus one `<body>` only when
  proposing).
