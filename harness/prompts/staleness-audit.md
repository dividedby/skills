# Monthly staleness-review pass

You are running unattended in GitHub Actions. No user is watching. Do not ask
questions — make the call yourself.

You **do not file anything yourself.** Your entire output is a single `<output>`
block at the very end of your response (schema below), followed by a `<body>`
block. A deterministic workflow step parses those blocks and publishes the issue
— this is what enforces the one-issue-per-run cap and the provenance label in
code rather than trusting the prompt. Do **not** run `gh issue create`; if you
do, you will create a duplicate.

## Task

This loop runs the in-repo staleness-audit skill **report-only** against this
repo and files its ranked report as a single issue per run. Read and follow the
skill from its path in the checkout — `skills/engineering/staleness-audit/SKILL.md`
— there is no slash command to invoke here; this prompt is the concrete wiring.

1. List prior reports labelled `source:staleness-review` (both open and closed)
   so you do not re-file an unchanged report:

   ```
   gh issue list --label source:staleness-review --state all --limit 100
   ```

   If a recent open report already says exactly the same thing (the same pins, the
   same gaps), emit a `skipped` output rather than filing a duplicate.

2. Follow `skills/engineering/staleness-audit/SKILL.md`. It walks the repo's Node toolchain pins
   (`.nvmrc` / `.node-version`, `engines.node` in `package.json`), classifies each
   gap via `skills/engineering/staleness-audit/lib/version_gap.py` (call it by
   path — do not re-derive the gap math in prose), and renders one ranked,
   **recommend-only** markdown table:

   ```
   target | file | current | latest | gap | EOL | risk | action | migration
   ```

   The skill is **observe-and-recommend**: no web calls, no file edits. `latest`,
   `EOL`, and `migration` read `unverified` / blank at this slice. Do **not** edit
   the repo and do **not** apply any change — there is no apply path on this cron.

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
  "title": "staleness-review: <concise summary, e.g. Node toolchain pins (3 findings)>",
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
  "reason": "Why no report was filed (e.g. no Node toolchain pins found, or an identical open report already exists)."
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
