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

   Take the single most recent **open** one (by creation date) — a closed or
   dismissed report carries no prior state to diff against (closed means
   "resolved," not "unchanged"). If the most recent report is closed, or none
   exists, that is the same as no prior state: proceed to a full scan. Do not
   walk further back to an older open report, and do not diff against a
   closed one.

   If a most-recent-open report exists, fetch its body:

   ```
   gh issue view <number>
   ```

   Parse the trailing `<!-- state: {...} -->` block from that body (schema in
   step 3) — this is the prior run's `as_of` date and per-finding status, for
   the delta-only refresh in step 3, which compares **only** against this
   most-recent-open report's state. A prior report filed before this
   convention existed has no such block; treat that as no prior state and
   proceed to a full scan. If the open report already says exactly the same
   thing (the same pins, the same gaps), emit a `skipped` output rather than
   filing a duplicate.

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

   End the body with an invisible state block, on its own line after the
   recommend-only note:

   ```
   <!-- state: {"as_of": "YYYY-MM-DD", "findings": [{"target": "...", "current": "...", "action": "..."}]} -->
   ```

   `as_of` is today's date. `findings` has one entry per ranked-table row,
   carrying just the row's identity (`target`/`current`/`action`), not the
   full migration prose — this is a compact fingerprint for the *next* run to
   diff against, not a second copy of the report. It is not part of the
   human-facing report — don't reference it in the prose above it. Escape
   every field value before it goes in the block: a literal `<` becomes
   `&lt;` (a version constraint like `<1.2.0` would otherwise read as markup
   or corrupt the comment) — required because `target`/`current`/`action`
   are scraped from toolchain files and upstream release pages, not authored
   text you control.

   **Delta-only refresh.** Compare this run's `findings` against the
   most-recent-open report's parsed state block (step 1) — never against a
   closed report's state. Escape this run's fresh `target`/`current`/`action`
   values the same way (`<` → `&lt;`) *before* comparing, so the comparison is
   escaped-form vs. escaped-form — the stored state is already escaped, and an
   unescaped fresh value (e.g. a raw `<1.2.0` constraint) would never match its
   stored `&lt;1.2.0` form and would look "changed" every run even when
   nothing moved. If every `target`/`current`/`action` triple (compared in
   escaped form) is unchanged, that is a valid, cheap "no changes since
   `as_of`" result — emit `skipped` (step 4) instead of re-filing an identical
   report. If anything changed (new finding, resolved finding, version bump, a
   newly past EOL date), file the report as usual — the ranked table still
   carries every current finding in full (never split findings across
   issues) — but open the lede by naming the delta explicitly (e.g. "1 new
   finding, 2 resolved, 1 unchanged since 2026-06-01") instead of presenting
   it as if there were no prior context.

4. If the audit finds no pins, or the report is identical to the
   most-recent-open report's parsed state (step 3's delta check), emit a
   `skipped` output. A closed prior report never triggers a skip on its own —
   only an open report with unchanged state does. Do not reach for something
   to file.

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
the recommend-only note, and — as its last line — the invisible
`<!-- state: {...} -->` block from step 3. No escaping at the block level —
write the body exactly as it should appear in the filed issue; the per-field
`<` -> `&lt;` escaping inside the state block's JSON values is step 3's own
rule, not a rule about this outer block. Do not include the <body> / </body>
markers in the prose itself.
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
