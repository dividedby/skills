# Onboard a repo with the staleness-review loop

This stands up `staleness-audit` as a scheduled
[proposal loop](./proposal-loop-harness.md) in any repo with a pinned toolchain.
It is a **publish-seam** member of the family (like the
[architecture-review loop](./arch-review-setup.md)) — no knowledge-mirror input
and no cross-repo channels — with one trait unique to it: the underlying skill
*can* mutate (its verify-gated **apply** station), but the loop runs it
**report-only**, so the cron never changes a file. **Read the harness doc first**;
this doc is only the deltas.

It scans the repo's toolchain pins (`.nvmrc`, `engines`, `.python-version`,
`go.mod`, `.tool-versions`, CI matrices, container `FROM` tags, installer hints),
validates each against upstream for latest/EOL/migration, and files **one ranked
report issue per run** — the complement to Dependabot, which owns library deps.

## What differs from the harness skeleton

- **Skill source:** `dividedby/skills` → `skills/engineering/staleness-audit`. The
  reusable body always clones `dividedby/skills` fresh and sets
  `SKILL_DIR=$RUNNER_TEMP/skills-src/skills/engineering/staleness-audit` — this
  is identical for both the home-repo canary (called via local `./`) and every
  consumer (called via `@claude-loops-v1`). The `uses:` ref form is the only
  home-vs-consumer difference; SKILL_DIR is the same for both. The prompt
  follows the skill **by file path** via a `@SKILL_DIR@` placeholder the
  reusable body substitutes at `cat`-time (`sed "s#@SKILL_DIR@#$SKILL_DIR#g"`) — the
  env-parametrization of [ADR 0015](../adr/0015-apply-agent-research-prompt-is-consumer-portable-via-env.md)
  applied to the staleness skill path, so one fetched-fresh prompt serves all
  callers from a single fresh clone.
- **Ecosystem-general.** The prompt does **not** assume Node. It tells the agent to
  scan whatever pins the repo actually has — Node (`.nvmrc`, `engines.node`),
  Python (`requires-python`/`python` in `pyproject.toml`, `.python-version`,
  `.tool-versions`), Go (`go.mod`), CI matrices, container `FROM` tags — per the
  skill's own scan station. A Python-only repo gets a Python report, not a
  `skipped: no Node pins`.
- **Provenance label:** `source:staleness-review`.
- **Cadence:** monthly, **first Monday** — `cron: "8 13 * * 1"` gated on
  `[ "$(date -u +%-d)" -le 7 ]` (POSIX cron can't express "first Monday", so it
  fires every Monday and a `first-monday-gate` job skips all but the first — see the
  harness doc's hash-stagger note). A toolchain pin drifts on the order of weeks, so
  a monthly pass catches a stale line without issue-spam (contrast the arch loop's
  3×/week Mon/Wed/Sat slot).
- **Input:** none to fetch — the input *is* the checked-out repo's pins. The skill
  reads `CONTEXT.md` + `docs/adr/` for risk framing if present, but needs neither.
- **Web is required for the validate station.** Grant **`WebSearch` + `WebFetch`**:
  the skill resolves latest version, EOL date, and migration path upstream (prefer
  the project release page / `endoflife.date`). **Without web access the audit
  still runs but self-degrades** — every finding is tagged `unverified: no web
  access` and nothing is ranked by EOL — so a loop wired without these tools files
  a far weaker report. This is the one tool the staleness loop needs that the
  arch-review loop also happens to grant.
- **Report-only on the cron — the apply station is suppressed.** The skill has a
  verify-gated auto-apply path (in-major bumps behind a per-bump verify+revert),
  but the loop grants **no `Edit`/`Write`** and the prompt runs the skill
  report-only, so the cron only ever *files a report*. `permissions: contents:
  read, issues: write` and `GITHUB_TOKEN` enforce the no-mutation invariant in the
  harness, not in prompt-adherence. (Auto-apply is for an interactive, watched run
  — never an unattended cron.)
- **No cross-repo writes**, so **no `ISSUES_TOKEN`** — only
  `CLAUDE_CODE_OAUTH_TOKEN`.
- **Deterministic publish, structured `<output>` + raw `<body>`.** Identical to the
  arch-review loop: the agent does **not** file the issue. It ends its run with a
  schema-validated `<output>` JSON block of short single-line fields
  (`status: proposed|skipped`, plus `title` / `oneLineSummary` /
  `candidatesConsidered`, or `reason`) and — when proposing — a separate `<body>`
  block of **raw markdown** carrying the ranked report table verbatim. The body
  rides the `<body>` seam precisely because a markdown table (pipe-delimited cells,
  code fences, quoted version strings) is unreliable to hand-escape inside a JSON
  string (see #117). The fetched-fresh **harness `publish` seam**
  (`harness/cli.py publish`, [ADR 0014](../adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md))
  parses the JSON, copies the `<body>` verbatim, and runs `gh issue create` — so
  the one-report-per-run cap and the provenance label live **in code**, and a
  missing/garbled block **fails the run loudly**. It is a *tested stdlib parser*
  ([ADR 0004](../adr/0004-runbook-helpers-are-python-stdlib.md)); the
  staleness-specific round-trip case (a body with table pipes) is pinned in
  `harness/tests/test_cli.py`.
- **Tools (read-only `gh` + web + python3):**
  `Bash(gh issue list:*) Bash(gh issue view:*) Bash(git log:*) Bash(git diff:*) Bash(git show:*) Bash(git blame:*) Bash(git ls-files:*) Bash(git status:*) Bash(python3 $SKILL_DIR/lib/:*) Read Grep Glob WebSearch WebFetch`.
  `Bash(python3 $SKILL_DIR/lib/:*)` is load-bearing: the skill's classify/EOL/rank
  stations run the stdlib helpers under `lib/` (`version_gap.py`, `eol.py`,
  `rank.py`) by path — without the grant the agent's helper invocations are
  permission-denied and it falls back to deriving gaps and rankings in prose.
  The agent gets only read access to the tracker and **no `Edit`/`Write`** — it can
  neither `gh issue create` nor mutate the repo, which makes the deterministic
  publish the sole filing path and keeps the cron report-only.

## Reference

`dividedby/skills` → `.github/workflows/staleness-review.yml` is the **home-repo**
thin caller stub; it calls the reusable body via local `./` (canary). Consumer
repos vendor a thin caller stub that pins `@claude-loops-v1` (#382):

```yaml
uses: dividedby/skills/.github/workflows/staleness-review-reusable.yml@claude-loops-v1
secrets:
  CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

The stub carries no `SKILL_DIR`, no provenance label, no `claude -p` flags — all
of that lives in the reusable body (`staleness-review-reusable.yml`), which clones
`dividedby/skills` fresh each run for the harness, the prompt, and the skill.
See [`proposal-loop-harness.md`](./proposal-loop-harness.md) for the canonical
thin-stub form (both home-repo `./` and consumer `@claude-loops-v1` variants).

## To propagate to another repo

1. Vendor the thin caller stub: create `.github/workflows/staleness-review.yml`
   in the target repo with `on: schedule` (derive the cron slot with the
   hash-stagger rule in [`proposal-loop-harness.md`](./proposal-loop-harness.md);
   or use the same `8 13 * * 1` Monday slot as skills for a first-Monday monthly
   cadence) + `workflow_dispatch`, and the `permissions:` / `uses:` / `secrets:`
   block shown in "Reference" above. No `SKILL_DIR`, no provenance label, no
   `claude -p` flags — those live in the reusable body.
2. Ensure the `CLAUDE_CODE_OAUTH_TOKEN` secret exists in the target repo.
3. Confirm the repo actually pins a toolchain — any ecosystem (Node, Python, Go, …),
   not just Node (otherwise the loop just files a `skipped` report each run —
   harmless, but pointless).
4. `workflow_dispatch` once to verify it files ≤1 report issue (or skips), then
   let the monthly cron take over.

A repo can run this loop alongside the
[architecture-review](./arch-review-setup.md) and
[Consumer](./consumer-setup.md) loops — independent jobs with separate provenance
labels, sharing only the harness.
