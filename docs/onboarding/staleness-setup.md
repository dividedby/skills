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
  prompt follows the skill **by file path** via a `@SKILL_DIR@` placeholder the
  envelope substitutes at `cat`-time (`sed "s#@SKILL_DIR@#$SKILL_DIR#g"`) — the
  env-parametrization of [ADR 0015](../adr/0015-apply-agent-research-prompt-is-consumer-portable-via-env.md)
  applied to the staleness skill path, so one fetched-fresh prompt serves the host
  and every downstream repo. The **home repo** sets `SKILL_DIR=skills/engineering/staleness-audit`
  and reads the skill straight from the `ref: main` checkout (no `cp -R`, no
  skill-discovery config). A **downstream** repo clones `dividedby/skills` into a
  temp dir and sets `SKILL_DIR` to that clone's
  `…/skills/engineering/staleness-audit` — no checkout pollution, the same
  substitution does the rest.
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

`dividedby/skills` → `.github/workflows/staleness-review.yml` is a working
**envelope** instance; the prompt + publish seam it calls live in the
fetched-fresh harness (`harness/prompts/staleness-audit.md`, `harness/cli.py`).
Copy the envelope and set `SKILL_DIR` + the provenance label for the porting repo.
The home-repo envelope reads `harness/` straight from its own `ref: main` checkout;
a downstream repo clones `dividedby/skills` into a temp dir for both the harness
and the skill — see [`proposal-loop-harness.md`](./proposal-loop-harness.md).

## To propagate to another repo

1. Copy the workflow envelope. The envelope itself is the **only vendored piece**
   (ADR 0014): the harness + skill it calls are cloned fresh from
   `dividedby/skills` each run, so prompt/seam fixes reach every Consumer
   automatically — but envelope changes (tool grants, `--model` pin,
   `--max-budget-usd`, cron) do **not** propagate and need a PR per Consumer.
2. Set `SKILL_DIR` to the cloned skill path
   (`$RUNNER_TEMP/<clone>/skills/engineering/staleness-audit`) so the prompt's
   `@SKILL_DIR@` resolves; keep the full tool scoping from the Tools bullet above
   (read-only `gh`, `WebSearch`/`WebFetch`, and the load-bearing `Bash(python3 $SKILL_DIR/lib/:*)`)
   and `permissions: contents: read, issues: write`.
3. Ensure the `CLAUDE_CODE_OAUTH_TOKEN` secret exists.
4. Confirm the repo actually pins a toolchain — any ecosystem (Node, Python, Go, …),
   not just Node (otherwise the loop just files a `skipped` report each run —
   harmless, but pointless).
5. `workflow_dispatch` once to verify it files ≤1 report issue (or skips), then let
   the monthly cron take over.

A repo can run this loop alongside the
[architecture-review](./arch-review-setup.md) and
[Consumer](./consumer-setup.md) loops — independent jobs with separate provenance
labels, sharing only the harness.
