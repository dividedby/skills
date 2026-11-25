# Repo-audit builds the report page with render.py

> **Status: Accepted** — maintainer decision (2026-11-24). **Amends [ADR 0042](./0042-repo-audit-becomes-a-read-only-report.md).**

## Context

ADR 0042 says the output is a private Artifact built from `template.html`, a
supporting file in the skill folder. It does not say who fills the template. The
template had grown to 1,244 lines with 69 distinct tokens and 20 repeat block names,
and a 200-line header of fill rules the main session was meant to follow by
hand. A hand fill is impractical at that size, so the last run wrote a scratch
generator: the one step that decides what the page says (verdict, severity
order, which sections exist, which links resolve) was unrepeatable and untested.
Issue [#708](https://github.com/dividedby/skills/issues/708) fixes that.

## Decision

- **A script builds the page.** `render.py` takes `findings.json` and a new
  `page-extra.json` and writes the page. `findings.json` is the source of truth
  for everything computed: the header's commit and branch, the verdict, the
  blockers, the scorecard and coverage tables, the finding rows, the "Since the
  last run" section. The rows are sorted by severity (Blocker, High, Med, Low),
  then by id, as a rule of the page; the verdicts and severities themselves are
  read, not computed. `page-extra.json` holds what only the main
  session writes: prose, the plan, the fleet-standards rows, extra tables,
  screenshots, mockups and research. `render.py` copies verdicts and severities
  from `findings.json` and never recomputes them.
- **`template.html` stays the one markup source.** `render.py` parses it at run
  time (repeat blocks, tokens, sections by `h2` id), so the markup is edited in
  one place. The header comment shrinks to the notes a person editing the markup
  needs; the fill rules live in `render.py` and its tests, and the prose rules
  the main session follows in `SKILL.md` Stage 6.
- **Both inputs are validated.** `findings.json` against its schema and
  `page-extra.json` against `page-extra.schema.json`, with the validator in
  `evals/findings_check.py` loaded by path. The page is written only when it has
  no leftover token, no dangling link, no duplicate id and no unbalanced tag.
  Text from `findings.json` is escaped; `page-extra.json` prose is trusted inline
  HTML, checked with an HTML parser against an allowlist of tags and attributes:
  other tags, event handlers, unsafe link schemes, `url()` and literal colours
  are refused.
- **A hand-filled page is a failure.** A report page not produced by `render.py`
  is a failure condition in `SKILL.md`. The scrub still runs on the page.
- **Screenshot downscaling stays a model step.** The script has no image library
  (standard library only), so the main session downscales to JPEG at about q70
  first and `render.py` embeds the file as it is.
- **Unchanged.** The read-only rule, the stages, the rubric's areas, the verdict
  rules and the severity scale, and the page's markup and look.

## Consequences

- The fill rules are code with tests (`render.test.py`), and a test fails when
  `template.html` gains a token, repeat block or section that `render.py` does
  not fill.
- The main session writes one JSON file instead of 1,244 lines of HTML. A mistake
  in it is an error message, not a broken page.
- A mockup frame other than the browser window needs a scratch copy of
  `template.html` passed with `--template`, since the CSS the frame adds lives in
  the template.
- The per-stage split of `SKILL.md` (stage files read when the stage starts,
  to cut the main session's upfront reading) lands in a follow-up change under
  #708, which amends this ADR or notes itself here.
