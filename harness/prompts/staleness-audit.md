# Monthly staleness-review pass

You are running unattended in GitHub Actions. No user is watching. Do not ask
questions — make the call yourself.

You **do not file anything yourself.** Your entire output is a single `<output>`
block at the very end of your response (schema below), followed by a `<body>`
block. A deterministic workflow step parses those blocks and publishes the issue
— this is what enforces the per-run issue cap and the provenance label in code
rather than trusting the prompt. This loop files **one ranked report per run**
(all findings ride in its table — never split them across issues). Do **not**
run `gh issue create`; if you do, you will create a duplicate.

## Tool-use constraint

Your shell commands: `gh issue list --label ...` (step 1) — `gh issue view` is
also allowlisted if you need to inspect a specific prior report; the read-only
git set (`git log`, `git diff`, `git show`, `git blame`, `git ls-files`,
`git status`); and `python3 @SKILL_DIR@/lib/...` for `version_gap.py` /
`eol.py` / `rank.py`. Invoke each unquoted, exactly as shown — quoting the path
changes the literal command string and breaks the allowlist's prefix match.
One singular call per item: a `for`/`while` loop, `bash -c`, or a piped command
is matched as one opaque string and denied, so looping over several issue
numbers or chaining the `lib/` scripts together will not go through. Everything
else is `Read`, `Grep`, `Glob`, `WebSearch`, `WebFetch`.

## Task

This loop runs the staleness-audit skill **report-only** against this repo and
files its ranked report as a single issue per run. Read and follow the skill from
`@SKILL_DIR@/SKILL.md` — the workflow substitutes `@SKILL_DIR@` for the skill's
real location (the checkout's `skills/engineering/staleness-audit` in the
skills-repo itself; the fetched-fresh clone path in a downstream repo). There is
no slash command to invoke here; this prompt is the concrete wiring.

1. List prior reports labelled `source:staleness-review` (both open and closed)
   so you do not re-file an unchanged report:

   ```
   gh issue list --label source:staleness-review --state all --limit 100
   ```

   If a recent open report already says exactly the same thing (the same pins, the
   same gaps), emit a `skipped` output rather than filing a duplicate.

2. Follow `@SKILL_DIR@/SKILL.md`. Its scan station walks **whatever toolchain pins
   this repo actually has** — do not assume one ecosystem. Match the repo's real
   conventions across, e.g., Node (`.nvmrc` / `.node-version`, `engines.node` in
   `package.json`), Python (`requires-python` / `python` in `pyproject.toml`,
   `.python-version`, `.tool-versions`), Go (the `go` directive in `go.mod`), CI
   matrices, and container `FROM` tags.

   Then run the skill's **validate** station: for each finding, use
   `WebSearch`/`WebFetch` to resolve `latest` upstream and fetch the pinned
   major's end-of-life **date** (prefer an authoritative source — the project's
   release page or `endoflife.date`). Classify each gap via
   `@SKILL_DIR@/lib/version_gap.py`, decide EOL pastness via
   `@SKILL_DIR@/lib/eol.py`, and feed `eol_passed` into `@SKILL_DIR@/lib/rank.py`
   for the ordering (call each by path — do not re-derive the gap math, the
   pastness check, or the ranking in prose). When a specific lookup genuinely
   fails, degrade that finding to `unverified: no web access` — never guess a
   version or EOL date; `unverified` is the per-lookup fallback, not the default.
   Render one ranked, **recommend-only** markdown table:

   ```
   target | file | current | latest | gap | EOL | risk | action | migration
   ```

   `latest`, `EOL`, and `migration` carry the validated values (or the per-row
   `unverified` fallback). The loop is **observe-and-recommend**: web access is
   for **reads only**. Do **not** edit the repo and do **not** apply any change —
   the skill's apply station is suppressed; there is no apply path on this cron.

3. **Draft the report as a `<body>` block (see the output contract).** Do not file
   it — just write it. The body must contain the rendered table verbatim, a short
   lede naming what was scanned, and a closing note that every `action` is a
   recommendation (no apply path on this loop).

4. If the audit finds no pins, or the report is identical to a recent open
   `source:staleness-review` report, emit a `skipped` output. Do not reach for
   something to file.

## Output contract

End your response with a small machine-parsed `<output>` JSON block, **followed
by** — only when filing — a `<body>` block holding the raw issue body.

The split is deliberate and load-bearing: the `<output>` JSON carries only
**short, single-line** fields, so it stays valid JSON. The report body — long
prose with an embedded markdown table whose cells are delimited by `|` pipes, plus
quoted version strings and code fences — goes in the `<body>` block as **raw
markdown**, where it needs **no JSON escaping**. Do **not** put the body inside the
JSON: a multi-paragraph string with unescaped `"` quotes, newlines, or table pipes
produces invalid JSON and the run fails.

Emit valid JSON in `<output>`, copy the field names exactly, and add no fields
beyond those listed. It has one of two shapes.

Filed a report this run — emit the `<output>` block, then the `<body>` block, in
that order, as the very last things you write:

```
<output>
{
  "status": "proposed",
  "title": "staleness-review: <concise summary, e.g. Python + container pins (3 findings)>",
  "oneLineSummary": "One-line description of the report, for the run summary.",
  "candidatesConsidered": ["finding 1", "finding 2"]
}
</output>
<body>
The full report body as raw markdown: a short lede, the ranked table verbatim,
and the recommend-only note. No escaping — write it exactly as it should appear in
the filed issue. Do not include the <body> / </body> markers in the prose itself.
</body>
```

Nothing fresh worth filing — emit only the `<output>` block, no `<body>`:

```
<output>
{
  "status": "skipped",
  "reason": "Why no report was filed (e.g. no toolchain pins found, or an identical open report already exists)."
}
</output>
```

Field rules:

- `status` — `"proposed"` or `"skipped"`. Required.
- `title` — required when proposed; ≤256 chars; begins with `staleness-review:`. Keep it on one line.
- `oneLineSummary` — required when proposed; one line.
- `candidatesConsidered` — required when proposed; non-empty array of short strings (the findings considered).
- `reason` — required when skipped.
- The `<body>` block — required when proposed, omitted when skipped; raw markdown, no JSON escaping.

## Rules

- **Read-only on the repo. You file nothing.** No commits, no edits, no
  `gh issue create`. The workflow publishes the issue (and applies the
  `source:staleness-review` label) from your `<output>` + `<body>` blocks. Your
  only job is to read, decide, and emit them.
- One report per run, maximum — and the workflow enforces it regardless.
- No questions. There is no user.
