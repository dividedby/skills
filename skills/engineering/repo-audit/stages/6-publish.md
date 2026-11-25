Shared rules (Execution boundary, run log, lenses, depth and budgets, failure conditions) are in [`SKILL.md`](../SKILL.md).

## Stage 6 — Publish

[`render.py`](../render.py) builds the page; nobody fills
[`template.html`](../template.html) by hand. Write `findings.json` and
`page-extra.json` (below), downscale each screenshot, then run
`python3 <skill folder>/render.py <scratchpad>/findings.json <scratchpad>/page-extra.json -o <scratchpad>/page.html`.
It takes everything computed from `findings.json` (the header's commit and
branch, the verdict, blockers, scorecard and coverage tables, finding rows,
Since the last run) and everything written from `page-extra.json`,
checks both against their schemas, and writes the page only when it has no
leftover token, dangling link, duplicate id or unbalanced tag. On an error it
prints one line per fault and writes nothing: fix the input, never the page.

Downscaling is a model step, since the script has no image library: embed each
screenshot at its original width up to 1,280 px, downscale only above that,
never upscale, as JPEG at about q70, and keep the page under the Artifact size
limit. `render.py` embeds the file as it is. Its output goes through the scrub
below like any other file.

Write `findings.json` from the verified findings; its shape is
[`evals/findings.schema.json`](../evals/findings.schema.json). Its top-level
sections:

- `profile`: the Stage 1 table, one `{fact, value, source}` object per row,
  the pinned commit and branch included. The owner, ownership test, trust and
  execute-answer rows are here too. Type, tier, line-count exclusions,
  packages and remote are rows here, and a type with no `types.md` entry is a
  `type` row marked "fallback profile". The `depth` row is here too.
- `lens_coverage`: one `{lens, read, chosen_by}` object per launched lens, from
  its coverage line, which on a Medium or Large tier repo names the sampling
  rule and gives counts for a sampled read (`read`, `chosen_by`). `lens` is the short name (`code`, `architecture`,
  `product`, `design`, `market`); a helper is not a lens and has no entry. A lens's areas are those the [lens table](../SKILL.md#lenses-depth-and-budgets)
  gives it, and `also_reported_by` below uses the same names.
- `findings`: one object per finding on the page, fleet-standards fails
  included, with these fields:
  - `id`: the page anchor: `fs-<row id>` for a fleet fail, otherwise
    `<area id>-<n>`.
  - `key`: stable across runs: `<area id>:<rule id or check>:<primary path>`.
    The rule id is the fleet row id; otherwise a short name for the check (a
    repo rule too: `rules.md` ids are per run, so they are not keys). For
    example `security:secret-scan:.github/workflows` on a web app or
    `ops-release:no-rollback:ops/deploy.sh` on an infra repo. Use these names
    when the check applies, so keys match across runs: `secret-scan` (a
    hard-coded secret), `stale-constant` (a dated value past its date),
    `doc-command-missing` (a documented command that does not exist),
    `duplicate-file` (identical files), `golden-mismatch` (the headline number
    differs from the hand computation), `stale-recorded-fixture` (a recorded
    response older than the code or API it stands in for, with no schema
    check), `empty-input-accepted` (an empty or default input taken as a real
    value); otherwise a short kebab-case name. A key reused from the previous run (Stage 4) keeps its old area id and check
    name, even when the finding's `area` now differs.
  - `area`: the area id from [`rubric.md`](../rubric.md).
  - `severity`: `blocker`, `high`, `med` or `low`.
  - `title`, `evidence`, `fix`, and `effort` (`S`, `M` or `L`).
  - `rule_source`: where the rule comes from (the fleet row's source cell, a
    repo document `file:line`, or a named standard), or `null`.
  - `also_reported_by`: the other lenses from Stage 4's merge; `[]` when none.
  - `package`: the package the finding is in, or `null`.
- `go_public`: the go-public feasibility result of a private repo, an object
  `{verdict, minutes_saved_per_month, basis, basis_reason, items}`: `verdict` is
  `ready`, `ready_after_cleanup` or `keep_private`; `minutes_saved_per_month` is
  the [`briefs.md`](../briefs.md#security-privacy-and-data) **Minutes saved**
  figure, a number, or `null`; `basis` is `measured` or `estimated` (`null` when the
  minutes are `null`); `basis_reason` is the Needs X or other reason from the CI
  cost table when the minutes are `null`, else `null`; `items` is one `{row, result, needs_history_rewrite}` object per
  checklist row that is not clear. `null` when the check did not run, with the
  reason as a `{method, reason}` entry in `coverage.skipped_methods` for
  `security`.
- `scorecard`: `overall` (`not_ready`, `ready_with_fixes`, `ready`, or
  `not_assessed` when no applicable area has a verdict), `blockers` (the ids of
  every Blocker) and `areas`, one object per rubric area: `area`, `applies`
  (boolean), `verdict` (`not_ready`, `ready_with_fixes`, `ready` or
  `not_assessed`), `not_assessed_reason` (a reason from the rubric's list, else
  `null`) and `top_finding` (the id of the area's most severe finding, else
  `null`). At `quick`, fill an area of a lens that was not launched only from
  the lens table, never from your own reading or another lens's report: it is
  `not_assessed`, reason "Depth: quick run, `<lens>` lens not launched", even
  when a finding touches it. List such a finding under an area of a launched
  lens, or as a lead. `render.py` refuses a `quick` document that gives one of
  these areas a verdict. Its `packages` field holds, for a monorepo, one object per package
  with `package`, `type`, `verdict`, `not_assessed_reason` and `top_finding` (an
  unselected package has verdict `not_assessed`, reason Not selected); `[]`
  otherwise.
- `coverage`: one object per rubric area: `area`; `read`, `ran`, `measured` and
  `browsed` (booleans for the methods used); `not_assessed_reason`, the same as
  the scorecard's; and `skipped_methods`, a list of `{method, reason}` for each
  method the area lists and the run did not use, a baseline tool or gate that
  did not run included, with its reason from the digest's Not run table.
  `measured` and `browsed` are true for `accessibility`, `content-branding`,
  `usability` and `performance` when probe cells ran for them, and
  `skipped_methods` holds one `{method, reason}` for each probe dimension that
  did not run (cells, keyboard pass, Lighthouse, the second instance).
- `diff`: only when the prompt gives a previous run's page link; otherwise
  leave it out. Use the `findings.json` Stage 1 read. When it cannot be read or
  fails the diff-input check (not the full schema), add a Guesses row, set
  `diff` to `null` and say so on the page. Otherwise
  `{previous_url, new, fixed, still_open, not_rechecked, not_reraised}`, each a
  list of `key`s, by the rules
  in `diff_runs` in [`evals/findings_check.py`](../evals/findings_check.py): `new`
  is in this run only; `still_open` is in both; a key in the previous run only is
  `not_rechecked` when its area is Not assessed now (a depth difference
  included) or a lens named it in its "Previous keys" line as not re-checked;
  `not_reraised` when the code did not change under its path between the two
  pinned commits (or the commits could not be compared); else `fixed`. The same
  commit never gives a `fixed`. The page gets a "Since the last run" section
  (computed by `render.py`) and marks a still-open item whose severity changed
  (a `since_notes` entry in `page-extra.json`).

### Page content

Write `page-extra.json` beside `findings.json`; its shape is
[`page-extra.schema.json`](../page-extra.schema.json), a sample is
[`evals/sample-page-extra.json`](../evals/sample-page-extra.json). It holds what
`findings.json` does not: prose, the plan, the fleet-standards rows, extra
tables, screens, mockups, research and the Stage 4 lists. A `prose` string is
inline HTML limited to text, link, list, table and inline-SVG tags;
`render.py` refuses any other tag (script, style, iframe, form, img), event
handlers, links other than `#`, relative, http, https and mailto, `url()` in a
style, and any literal colour (a fallback inside `var()` included), so use only
the page's custom properties (`--ink`, `--accent`, `--hi`, `--good` and the rest the template
lists; mockups only `--mk-*`). Cells, plan text and notes may carry a pill, a
link or code. Intros are one or two sentences that add what the tables do not. Finding rows
are sorted by `render.py`, not by `findings.json`: Blocker, High, Med, Low, then
by id (numeric part as a number); a fleet fail has no finding row.

- **Trust and method** (`method_note`, `overall_text`). `method_note` states how
  the run treated the repo's code: "trusted" (with the ownership leg that
  passed, the no-remote result or the prompt), "untrusted, run allowed (answered
  HH:MM CT)", or "untrusted, not run (answered no HH:MM CT, no answer by HH:MM CT,
  or not asked: reason)". `overall_text` names every area that lost a method or
  was Not assessed because of it, with the reason Untrusted not run; the Coverage
  reasons and one `checked.unverified` line per skipped method carry it too. It
  also says there are no Blockers when none, and names every applicable area
  that is Not assessed; a `quick` run names each one Not assessed (depth) with
  its lens ("Depth: quick run, `<lens>` lens not launched").
- **Depth, budget, run log.** `method_note` states the depth, the run's wall
  time and agent tokens against the budget in [`SKILL.md`](../SKILL.md#lenses-depth-and-budgets) (a measure over by more
  than 50% named, with by how much) and the main-session reading line
  (skill lines read per stage and summed, and the context size at each stage end),
  reported, not budgeted. It links `run-log.md` and `findings.json`, and the
  report file of each lens that ran, all beside the page (design: copy table,
  brand inventory, walkthrough logs; code: benchmark and test-suite evidence;
  architecture: store, personal-data, outbound-call and module depth tables and
  the go-public checklist; product: install log, error-copy log, CI cost table;
  market). It names every partial or failed lens, and a skipped market lens with
  its reason (the market test, or "standard four-agent cap"). A lens that failed
  with no output leaves each area it owns Not assessed, "lens failed: reason", in
  `findings.json`; a partial lens keeps its verdicts and says "Partial" with the
  reason in its Coverage reasons, area intros and `checked.unverified` line. No
  area is left without a verdict or a Not-assessed mark.
- **Area intros** (`intros.<area id>`). A section exists for each area with
  findings; write an intro for it. An intro also keeps a section with no
  findings, and the section's finding table is then left out. Write one for
  `external-facts` when facts were checked, `agent-readiness` whenever the area
  applies, `repo-hygiene` whenever it is assessed, `security` for a private repo
  when go-public feasibility ran or was skipped with a reason, and `ops-release`
  when the repo has CI workflows. A Not-assessed area has none (the scorecard
  and Coverage carry its reason). Fold "why it matters" into a finding's
  `title`. The areas a lens report feeds link its file: the design report from
  `accessibility`, `content-branding` and `usability`; the code report from
  `code-quality`, `tests` and `performance`; the architecture report from
  `architecture`, `data-integrity`, `privacy` and `security`; the product report
  from `ops-release`. A report's tables are not on the page; its findings are
  finding rows citing the report section. For a private repo the `security`
  intro states the go-public verdict (Ready, Ready after cleanup or Keep private),
  the items and which need a history rewrite, and the minutes a month going
  public would save with `go_public.basis`, or `go_public.basis_reason` when
  null; with the check not run it gives the reason from `rubric.md`. The
  `ops-release` intro, when the repo has CI workflows, gives the billable minutes
  a month and their share of the included minutes, each labelled measured or
  estimated, and the minutes the cuts would save; with no workflow, the reason.
  Keep both sections for those sentences even with no findings.
- **Fleet standards** (`intros.standards`, `standards.rows`). The intro gives the
  checklist source and commit, how it was read, the repo facts, counts per result
  and the fails split into quality and process. When the checklist could not be
  read, the repo is not a fleet repo or it has no remote, `rows` is `[]` and the
  intro says "n/a (not a fleet repo)" with the ownership test's result, or
  "Not assessed (Needs X: a remote)", or the reason. One row per checklist row,
  n/a rows included. A report-only row shows OK (`pass`) or FLAG (`unchecked`,
  with a severity). A fleet fail is a row, never a finding row: its finding in
  `findings.json` has id `fs-<row id>`, and the scorecard link to it resolves to the row.
- **Rules conformance** (`intros.rules`, tables in section `rules`). The intro
  names the source files read and the counts (pass, fail, not assessed); with no
  rules harvested it says so and there are no tables. Two tables: counts per
  source file (Source, Rules, Pass, Fail, Not assessed; a source with fails
  first), then the rows that did not pass, fails first (Rule: id and text;
  Source: `file:line`; Result: `res fail` FAIL or `res unchecked` NOT ASSESSED;
  Evidence: the finding's evidence, or the not-assessed reason from
  `rubric.md`; Link: the finding's id, an em dash for a not-assessed row). Passes
  are counts only. A failed row is also a finding in its area whose title names
  the rule and its source.
- **Area tables** (`tables`, section = the area id), each before the finding
  table. External facts: Fact (name and the value the repo holds), File:line,
  Source URL (a link), Date read, Result (`res pass` MATCH, `res fail` MISMATCH,
  `res unchecked` COULDN'T VERIFY, with the reason); mismatches first, each also a
  finding; with candidates left by the cap, a last row "Not checked: N more"
  (`res unchecked` NOT CHECKED, where they live in File:line, em dashes in Source
  URL and Date read). The intro says how the values stay current (the update step,
  pinning test or warning with its file:line, or none) and gives the counts.
  Agent readiness: Gate, Documented at (`file:line`, per the rubric's Documented
  gates check), As written (ran as written, ran with a change and what, failed as
  written, or not run with its reason), Result (`res pass` PASS, `res fail` FAIL,
  `res unchecked` NOT RUN, with the counts), Time, Manual steps (what the doc leaves out, or
  an em dash); one row per gate in the baseline digest's Gates table, fails first. Its intro names each agent file
  with lines and words (reported, not scored), the focused test command and its
  wall time or that there is none, the counts (stale paths or commands,
  duplicated items), and the sampled-issues result or its skip reason. With no
  agent file it says so; with no gate documented anywhere it says that and
  there is no gates table. Each stale
  path, command and duplicate is a finding row with its `file:line` (both for a
  duplicate). Repo
  organisation: Path, Kind (digest item, scratch directory, orphan doc,
  commented-out code, stale marker), Evidence (the test it failed), Finding (its
  id as a link, or an em dash); one row per item with its own path, the baseline
  digest's top 10 as "digest item" rows and a last row "Digest: N more" naming
  where the rest live. Its intro gives the structure counts (top-level folders
  and files, maximum depth and its deepest path, top-level source folders with a
  findable public surface; on a Small tier repo "Depth: Small tier, counts and
  depth only"), the glossary, lean-report and ADR results, and every skipped
  check with its reason from the rubric's Skips. An avoided term still used is a
  finding whose evidence gives the `git grep` hit count, the count judged in
  sense and up to five `file:line` samples.
- **UI probe** (`intros.measurements`, tables in section `measurements`). Keep
  it when a probe cell ran; when a web UI was in scope and no cell ran, the
  Dimensions not run table alone; otherwise write no intro. The intro names how
  the instances were isolated, that both were stopped before Stage 4, the
  matrix size (screens, states, widths, themes, cells) and that every figure is a
  lab or probe measurement on throwaway data. Tables, in order: Totals per
  screen (Screen, Cells run, Cells failing, Axe violations, Overflow, Small
  targets, Console and failed requests, Copy flags; failing screens first). Copy flags
  are sentences over the limit, the longest block in words, the highest mean
  sentence length, plain-prose blocks over the limit (`briefs.md` Copy density
  holds the limits) and repeated blocks; a summary row with `spaceDelimited`
  false has no word figures, and long unstructured blocks are counted but never
  fail a cell (the design lens flags them on primary flows);
  Failing cells (Screen, Cell: state, width and theme; Check; Detail: the rule,
  impact and count, the offending selector or the measured size; Link; at most
  30, worst first, a last row "N more in the probe JSON"; passing cells are
  counts in table 1, never rows); Lighthouse for hosted sites (Metric each
  labelled "(lab)", Value, Threshold or budget, How measured) with one row per
  keyboard flow (Flow, Steps, Result as `res pass` or `res fail`, First failing
  step); Dimensions not run
  (Dimension, Reason). A failing check that matters is also a finding in its
  area: axe, targets and overflow in `accessibility`, copy metrics in
  `content-branding`, Lighthouse in `performance`, keyboard failures in
  `usability`, each with its id in the Link cell. `intros.screens` says which
  cells were captured and why.
- **Coverage** (`intros.coverage`). States the size tier, the line-count
  exclusions and the detected types (per package in a monorepo), and names any
  type with no `types.md` entry as "fallback profile". The tables come from
  `findings.json`.
- **What was checked** (`checked`, one line per item). `merged` holds the kept
  finding's id and the lenses it also came from; for a fold, the fleet-standards
  row id; for a linked pair, both ids; for a re-areaed finding, its id and both
  areas; for a reused key, the key and the previous finding's id. `disputed`
  holds both readings and which the evidence favours.
- **Plan** (`plan`). Items link to a finding id on the page, `fs-<row id>` or
  `research`; an item resting on market output links `research`. Every Blocker
  is in Now.
- **Screens, mockups, research** (`screens`, `mockups`, `research`). With no
  capture (no UI, every capture dropped for privacy, or a `quick` run) leave
  `screens` out and write "No captures: reason" in `method_note`. Mockups exist
  only for a High or Blocker design finding, at most three, each showing its
  rewritten copy; otherwise leave `mockups` out and write "No mockups: reason"
  in `intros.screens`, or `method_note` with no Screens section. Market output
  is context, not an area: it appears in `research` and as evidence in External
  facts and Tech stack findings.

### Publish files

The page ships with `run-log.md`, `findings.json` and the report file of every
lens that ran (code, architecture, product, design, market), beside it through
the Artifact `files` map, each linked from the page. Every file that leaves the
scratchpad, those side files included, takes the same five steps:

1. **Finish the files.** The page, `findings.json`, each lens report and any
   other file bound for the `files` map are final, and the log has its
   read-only proof and its totals. The preview row and the Scrub section come at
   **Record, check, publish**.
2. **Read the demo data.** Demo, sample, fixture and seed data is untrusted: a
   repo's demo can hold a real address, a real person's name or a location. Read
   the page's text and captions, and the lens reports, for the kinds the Privacy
   method's personal-data table names ([`briefs.md`](../briefs.md)), plus real
   places, and replace each with made-up text. Check the empty and first-run
   captures, and the report text that quotes them, for values the app fills in
   by default (a default ZIP, city or name); `private-literals.txt` lists what
   to look for (its value field). A screenshot that shows one is retaken from clean data or
   cropped. The scrub is a floor, not a substitute:
   it matches shapes, cannot tell a real name or address from a made-up one,
   and skips the page's embedded `data:` images. A finding seen here goes back
   through Stage 4 as an added finding.
3. **Scrub.** Copy every file into one folder, `<scratchpad>/publish/`, the
   page and the log included, and run `python3 <skill folder>/scrub.py <publish>/*`
   on all of them, adding `--literal <value>` for each line of
   `<scratchpad>/private-literals.txt` (the value field), passed first so the
   warning's K is the file's K-th line, and for any user name the machine's own
   names do not cover, and `--hostname <name>` for a host name. `--literal`
   takes any private string: a name, a place, a ZIP, an account or device id.
   A `scrub: warning: literal #K matched M times` on stderr means the K-th
   `--literal` passed (line K of the file) is probably a common word: drop it,
   copy the files into the publish folder afresh (the first run already
   rewrote them) and rerun.
   The log records how many literals were passed, never their values. It
   rewrites each file in place, putting a `[redacted:<category>]` placeholder in
   place of each match, and prints counts per file and category, never values.
   The categories are home and scratch paths, user and host names, IP
   addresses, account ids, Apple team and device ids, tokens and keys, emails,
   coordinates and the literals passed; the
   script's header lists each rule and what it leaves alone. No published file
   is skipped, and a file that is not text stops the run. From here on, the
   preview and the publish read this folder.
4. **Preview.** Serve the folder; do not open a `file://` page, which the
   browser pane refuses for a scratchpad file, and do not use the dev-server
   preview, which needs a project config the scratchpad lacks. Pick a free port
   (`python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'`),
   start `python3 -m http.server <port> --bind 127.0.0.1 --directory <publish>`
   in the background, open `http://127.0.0.1:<port>/<page file>` in the browser
   pane through its url option, and look at light and dark, desktop and phone
   width. Stop the server before **Record, check, publish**. A fix to the page goes back
   to **Read the demo data** with the new page. With no browser pane, skip the
   server: publish privately at **Record, check, publish**, read the page back
   with the Artifact read action, check it there, and republish from **Read the
   demo data** through **Record, check, publish** if it needs a fix.
5. **Record, check, publish.** In the log's publish copy and in the scratchpad
   original, add the preview server as a `process started` row and write the
   `## Scrub` section from the **Scrub** summary. The `run-log.md` row counts what
   the scrub removed from the log before this section existed; the section holds
   only counts and names, so it adds nothing for the check to find. Then run
   `python3 <skill folder>/scrub.py --check <publish>/*` with the same `--literal` and
   `--hostname` flags as **Scrub**. It must exit 0 over every file, the
   log included, before anything is published; on exit 1, fix the cause and
   repeat from **Scrub**.

Publish as a **private** Artifact, from the publish folder. If the Artifact tool
offers a `quickstart`, run it (it is read-only), then keep the page `render.py`
built, which already meets the page contract. Where the Artifact tool is unavailable,
send the publish folder's page, `run-log.md` and `findings.json` to the user as
files.

Close with a short message: the link, the overall verdict with any Blockers
by name, one line per area (its verdict, or its Not-assessed reason), a line
for the fleet-standards section (counts per result, with fails split into
quality and process, and the checklist commit, or "n/a (not a fleet repo)", or "Not assessed (Needs X: a remote)"), a trust line
(the ownership result and the execute answer, with the areas it cost), a
line for Rules conformance (pass, fail and not-assessed counts, rolled up from the lenses' rules blocks),
the top findings, what was verified and what was not, the run's totals (wall time and
agent tokens, against the budget, with any measure over by more than 50% named
and by how much, and the main-session reading line, reported not budgeted), the
number of guesses, any partial or failed lens, the areas Not assessed (depth) on
a `quick` run, with a previous run's link the five `diff` counts on one line (new,
fixed, still open, not re-checked, not re-raised), and confirmation that the repo is unchanged, or each breach found (gate and path) for the maintainer to remove. When the
run reports to the user, end with **one question** — which part of the plan to
start on — and offer `/to-tickets` for the plan in one line. When it reports to
another session, end with the page link and the plan's first item instead.

**Done when:** the page is published (or sent) with the run log and
`findings.json` beside it, every published file went through the scrub and the
final check passed, the repo shows no changes (`mtime only` rows and writes
inside nested worktrees are not changes), and the closing message names
what is unverified and any partial or failed lens.
