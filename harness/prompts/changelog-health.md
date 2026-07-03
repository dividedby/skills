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

### 5. Critique the eval criteria itself

Every run does this step — whether step 3 landed on "proposed" or "skipped".
You just graded this repo's changelog against the eight-row checklist in
`docs/agents/changelog-guideline.md`; now grade the checklist itself. Look
for:

- **Blind spots** — an assertion a clearly-wrong changelog would still pass.
  E.g. could a changelog with a breaking change buried in `Added` instead of
  flagged `**Breaking:**`, or with every entry a bare `(#123)` and no prose,
  slip through all eight rows clean?
- **Uncovered outcomes** — something this repo's changelog should plainly get
  right that none of the eight rows would ever catch.
- **Unverifiable criteria** — a row phrased so you cannot mechanically decide
  pass/fail from the diff plus `git log` alone, and had to guess.

This is a critique of the rubric, not of the repo. It is **flag-only** (ADR
0034: never rewrite) and it is **not actionable by this loop** — you do not
edit `docs/agents/changelog-guideline.md`, propose a rewrite of it, or fold it
into the advisory in step 4. It exists so the human who owns the rubric can
see where it's thin. If nothing is worth flagging, omit the block entirely —
"the checklist held up" is a valid, cheap non-finding and needs no block.

## Output contract

End your response with a small machine-parsed `<output>` JSON block, **followed
by** — only when proposing — one `<body>` block holding the raw advisory, and
**optionally, every run** — proposed or skipped — one `<eval_feedback>` block
(step 5's rubric critique).

The split is deliberate and load-bearing: the `<output>` JSON carries only
**short, single-line** fields, so it stays valid JSON. The advisory body — long
prose with embedded markdown — goes in the `<body>` block as **raw markdown**,
where it needs **no JSON escaping**. Do **not** put the body inside the JSON.

`<eval_feedback>` is a third, independent block, also raw markdown, also
outside the JSON. It is not part of the advisory the workflow files — nothing
in the publish pipeline reads it or acts on it; it is a flag for a human to
read later, never a proposal. Omit it when step 5 found nothing to flag.

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
<eval_feedback>
Optional. Only present when step 5 found something to flag. Raw markdown, a
few bullets naming the rubric blind spot, uncovered outcome, or unverifiable
criterion. Not filed, not acted on — for the rubric owner only.
</eval_feedback>
```

Nothing to flag — emit only the `<output>` block, no `<body>` — and still,
optionally, an `<eval_feedback>` block if step 5 found something to flag:

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
- The `<eval_feedback>` block — optional, either shape, present only when
  step 5 found a rubric blind spot, uncovered outcome, or unverifiable
  criterion to flag; raw markdown, no JSON escaping.

## Rules

- **Read-only. You file nothing.** No commits, no edits, no `gh issue create`,
  no `gh issue comment`. The workflow publishes the advisory (and applies the
  `source:changelog-health` label) from your `<output>` + `<body>` blocks.
  The workflow's publish step also handles dedup (single-open-advisory) via
  `--dedup-open` — you do not need to check for open advisories yourself.
- **Flag, never rewrite.** The advisory proposes entries the maintainer
  hand-applies. It never modifies `CHANGELOG.md` or any other file.
- **`eval_feedback` is non-actionable by this loop.** It is a flag for the
  human who owns `docs/agents/changelog-guideline.md`, not an instruction to
  the loop and not part of the filed advisory. The loop never edits the
  rubric doc, never treats a rubric critique as grounds to change grading
  behavior mid-run, and never files it as its own issue.
- **No questions.** There is no user.
- End every run with exactly one `<output>` block (plus one `<body>` only when
  proposing, plus one optional `<eval_feedback>` either way).
