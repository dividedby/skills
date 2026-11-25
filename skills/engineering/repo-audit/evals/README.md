# repo-audit evals

Synthetic fixture repos with expected results, a schema for `findings.json`, and
an on-demand runner. Not a skill: [`SKILL.md`](../SKILL.md) links here.

## What is here

| File                   | Purpose                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ |
| `fixtures.py`          | Generates the six fixtures as git repos into a folder you name. Deterministic: same commit SHAs each run     |
| `expectations.json`    | Per fixture: type, tier, applicable areas, and the planted findings to match by `key`                        |
| `findings.schema.json` | The shape of `findings.json` (SKILL.md Stage 6)                                                              |
| `findings_check.py`    | Schema validator, expectation checks, the cross-run `diff_runs` rule and its input check, all pure functions |
| `sample-findings.json` | A schema-valid sample that passes `single-script` at `quick`; the self-test's input                          |
| `evals.test.py`        | CI self-test: no `claude` call, stdlib and `git` only, about 3-5 s                                           |
| `run_evals.py`         | The paid runner                                                                                              |

Run the self-test: `python3 -B skills/engineering/repo-audit/evals/evals.test.py`.
CI's `gate` job runs it with the other `*.test.py` files.

## Fixtures

Each fixture has 4 commits, no remote, and four planted defects: a hard-coded
secret, a stale dated constant (`2019-12-31`), a README command that does not
exist, and a duplicate file. `single-script` plants a fifth: a recorded API
response (`tests/recorded/fee_schedule.json`, recorded 2021-06-02) that no
schema check covers. The secret is a fake token assembled at runtime, so
no committed file holds it. Nothing is real; emails are `@example.invalid`.

| Fixture           | Shape                                                                        | Tier   | Used by the runner |
| ----------------- | ---------------------------------------------------------------------------- | ------ | ------------------ |
| `single-script`   | One Python script, config, README, a copy of the script, a recorded response | Small  | yes                |
| `docs-only`       | Markdown and YAML, no tracked source                                         | Small  | yes                |
| `unknown-type`    | A Verilog design; matches no `types.md` entry, so a fallback profile         | Small  | yes                |
| `workspace`       | pnpm workspace, 3 packages, about 3.5k source lines                          | Medium | no                 |
| `static-site`     | Static HTML and CSS with an overflow and a low-contrast pair                 | Small  | no                 |
| `large-workspace` | pnpm workspace, 6 packages, about 113k generated source lines in 618 files   | Large  | no, on demand      |

`large-workspace` is generated, not checked in. Its source is cheap and varied
JS (five function shapes rotated by package and module) with nothing the tier
rule excludes, so `types.md` sets the Large tier. Its defects sit where a
Large-tier sample is bound to reach them: the token is found by the whole-repo
secret scan, the stale constant is in a package entry point (`index.js`), the
duplicate pair are the two largest tracked files, and the README is always read.
The runner skips it by default (a Large audit costs far more than the three
default fixtures; run it with `--fixtures large-workspace`), and skips
`workspace` (about twice the tokens) and `static-site` (it needs the design
lens, which `quick` does not launch). The self-test generates all six.

## Expectations

Read from `findings.json`, never from prose:

- **type and tier:** the profile's `type` and `tier` rows (`type_regex`, `fallback`, `tier`; `packages_min` counts the scorecard's package rows).
- **lens coverage:** a fixture with a `lens_coverage` regex (`large-workspace`) fails unless the findings have `lens_coverage` rows and each row's `read` and `chosen_by` text matches it (a sample, random, churn, largest or entry-point statement). Other tiers read everything, so they set no regex.
- **applicable areas:** `areas` maps an area id to `true` or `false` (checked against the scorecard's `applies`), or `null` when the rubric leaves it to judgement (not asserted).
- **planted findings:** a finding matches on its `key`, split into `<area>:<check>:<path>`: the key's area is in the expectation's `areas`, its path is in `paths`, and its check name matches the `check` regex (case-insensitive). The finding's own `area` field is not used. Area and path follow from the fixture; the check name is the model's wording, so the regex is loose and `SKILL.md` fixes the canonical names. A failure prints the nearest finding.
- **depth gaps:** `quick` launches only the `code` and `architecture` lenses. A planted finding whose owner lens did not run (`checked_at` lacks `quick`) is checked as a depth gap instead: its `gap_area` is Not assessed with a reason starting `Depth`. The README command, the docs-only duplicate and the static-site findings are asserted as findings only with `--depth standard`.
- **no silent gap:** all 16 areas have a scorecard row and a coverage row; every not-applicable or Not-assessed area has a reason.
- **repo unchanged:** the runner compares `git status --porcelain --ignored`, `HEAD` and a hash of every file outside `.git` before and after.

## Not covered here

Instance restarts. The fixtures are synthetic repos with no web UI, so a run
starts no instance, and the run log is not in `findings.json`. The restart path
(`SKILL.md` Stage 3 curls each instance and restarts a down one as a background
task on the same port and data directory; the `process restarted` row in
[`run-log.md`](../run-log.md)) is checked by reading a real web-UI run's run log:
every instance a lens used was up or has a `process restarted` row, and no lens
started an instance of its own.

## Run the runner

```text
python3 skills/engineering/repo-audit/evals/run_evals.py --dry-run   # spends nothing
python3 skills/engineering/repo-audit/evals/run_evals.py             # paid
```

`--dry-run` generates the fixtures (free) and prints the exact `claude -p`
command for each. Options: `--fixtures a,b`, `--depth quick|standard`,
`--max-budget-usd` (default 10 per fixture), `--out DIR`, `--plugin-dir`,
`--skill` (default `/dividedby-skills:repo-audit`, the plugin name from
`.claude-plugin/plugin.json` and the skill name), `--claude`, `--timeout-min`.

Each fixture is one headless `claude -p` call in the fixture folder with
`--permission-mode dontAsk` and `--allowedTools Read,Grep,Glob,Write,Bash,Agent,WebSearch,WebFetch`.
Those are what a `quick` run uses: read and search, write the lens reports,
run git and the baseline, launch lenses, check external facts. The Artifact
tool and any publish or send tool are not allowed, so the skill saves the page
and `findings.json` to its scratchpad as it does when it cannot publish; the
prompt also asks it to copy `findings.json` into the run's output folder. The runner reads that copy, else a `findings.json` path named in the run's result, and accepts only a file written after the run started (earlier output files are deleted before each run). It does not scan the temp folders: another session's file could match. `--disallowedTools Artifact` backs up the allow list. `Edit`
is not allowed: the audit is read-only, and `Bash` is broad, so safety rests on
the throwaway synthetic repo and the unchanged check.

The runner prints a table of `fixture | expectation | PASS/FAIL | detail`, then
cost per fixture (USD, tokens, wall time) and a total, writes `summary.json` and
each run's `result.json` under the output folder, and exits 1 on any failure.

Cost: about 150k agent tokens per fixture at `quick`, so a full run is roughly
450k tokens. The budget cap per fixture ends a run early; a capped run has a
partial or missing `findings.json` and reports FAIL rather than crashing. Wall
time is tens of minutes in all.

## Why not `claude plugin eval`

Read from `claude plugin eval --help`, not trialled. By default it runs each case
3 times plus a no-plugin baseline arm, which multiplies the cost of a
150k-token audit several times over, and it publishes its HTML report to
claude.ai. Building a fixture repo per case needs an author-supplied
`scaffold_script` that runs bash as you. The checks here (match findings by
`key`, validate the schema, prove the repo is unchanged, record each run's cost)
are plain code over one run's files, so a small stdlib runner around `claude -p`
does them directly and spends one run per fixture.
