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

- **Skill source:** `dividedby/skills` → `skills/engineering/staleness-audit`. It
  is **local to this repo**, so the home-repo envelope reads it straight from the
  `ref: main` checkout — no `cp -R` into `~/.claude/skills/` and no skill-discovery
  config, because the prompt follows the skill **by file path**
  (`skills/engineering/staleness-audit/SKILL.md`). A *downstream* repo clones
  `dividedby/skills` into a temp dir and points the prompt at that path.
- **Provenance label:** `source:staleness-review`.
- **Cadence:** monthly — `cron: "37 11 1 * *"` (1st of the month, off-the-hour). A
  toolchain pin drifts on the order of weeks, so a monthly pass catches a stale
  line without issue-spam (contrast the arch loop's weekday cron).
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
- **No cross-repo writes**, so **no `SKILLS_TRACKER_TOKEN`** — only
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
- **Tools (read-only `gh` + web):**
  `Bash(gh issue list:*) Bash(gh issue view:*) Bash(gh search:*) Bash(gh api:*) Bash(git:*) Read Grep Glob WebSearch WebFetch`.
  The agent gets only read access to the tracker and **no `Edit`/`Write`** — it can
  neither `gh issue create` nor mutate the repo, which makes the deterministic
  publish the sole filing path and keeps the cron report-only.

## Reference

`dividedby/skills` → `.github/workflows/staleness-review.yml` is a working
**envelope** instance; the prompt + publish seam it calls live in the
fetched-fresh harness (`harness/prompts/staleness-audit.md`, `harness/cli.py`).
Copy the envelope, change only the skill path and label if porting to another
repo. The home-repo envelope reads `harness/` straight from its own `ref: main`
checkout; a downstream repo clones `dividedby/skills` into a temp dir for it — see
[`proposal-loop-harness.md`](./proposal-loop-harness.md).

## To propagate to another repo

1. Copy the workflow envelope (it clones the harness fresh; nothing else to vendor).
2. Ensure the `CLAUDE_CODE_OAUTH_TOKEN` secret exists.
3. Confirm the repo actually pins a toolchain (otherwise the loop just files a
   `skipped` report each run — harmless, but pointless).
4. `workflow_dispatch` once to verify it files ≤1 report issue (or skips), then let
   the monthly cron take over.

A repo can run this loop alongside the
[architecture-review](./arch-review-setup.md) and
[Consumer](./consumer-setup.md) loops — independent jobs with separate provenance
labels, sharing only the harness.
