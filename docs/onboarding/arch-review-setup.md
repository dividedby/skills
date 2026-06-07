# Onboard a repo with the architecture-review loop

This stands up `improve-codebase-architecture` as a scheduled
[proposal loop](./proposal-loop-harness.md) in any repo with code worth
reviewing. It is the **leanest** member of the family in terms of wiring — **no**
knowledge-mirror input and **no** cross-repo channels — though it adds one
refinement over the bare harness: a **deterministic publish seam** (below). It
reads the codebase itself — informed by `CONTEXT.md` + `docs/adr/` if present —
and files refactor proposals into the repo's own tracker. **Read the harness doc
first**; this doc is only the deltas.

## What differs from the harness skeleton

- **Skill source:** `mattpocock/skills` →
  `skills/engineering/improve-codebase-architecture` (not `dividedby/skills`).
- **Provenance label:** `source:architecture-review`.
- **Input:** none to fetch — the input *is* the checked-out repo. The skill reads
  `CONTEXT.md` + `docs/adr/` for domain language; without them it still runs, just
  blind to the repo's vocabulary.
- **No cross-repo writes**, so **no `SKILLS_TRACKER_TOKEN`** — only
  `CLAUDE_CODE_OAUTH_TOKEN`. `permissions: contents: read, issues: write` and
  `GITHUB_TOKEN` suffice.
- **Deterministic publish, structured `<output>` + raw `<body>`.** The agent does
  **not** file the issue. It explores, decides, and ends its run with a small
  schema-validated `<output>` JSON block of short single-line fields
  (`status: proposed|skipped`, plus `title` / `oneLineSummary` /
  `candidatesConsidered`, or `reason`) and — when proposing — a separate `<body>`
  block of **raw markdown** for the issue body. The body is kept out of the JSON
  on purpose: a long body with embedded code and quoted text is unreliable to
  hand-escape inside a JSON string, and a single unescaped `"` invalidates the
  whole block (see #117). The **harness `publish` seam** (`harness/cli.py publish`,
  fetched fresh — [ADR 0014](../adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md))
  parses the JSON, copies the `<body>` verbatim, and runs `gh issue create` — so
  the one-proposal-per-run cap and the provenance label live **in code**, not in
  prompt-adherence, and a missing/garbled block **fails the run loudly** rather
  than skipping silently. It is a *tested stdlib parser*, replacing the brittle
  `sed`/`jq` hand-escaping that caused #117/#211. It writes the step summary
  (outcome + candidates considered) itself; an `if: failure()` step surfaces the
  raw log when it fails. This is the generator/publisher split adapted from
  `mattpocock/course-video-manager`'s `architecture-review.yml`; the harness gives
  us in tested Python what it gets from the sandcastle framework.
- **Tools (read-only `gh`):**
  `Bash(gh issue list:*) Bash(gh issue view:*) Bash(gh search:*) Bash(gh api:*) Bash(git:*) Read Grep Glob WebSearch WebFetch`.
  The agent gets only read access to the tracker — it *cannot* `gh issue create`,
  which makes the deterministic publish the sole filing path.

## Reference

`dividedby/skills` → `.github/workflows/improve-codebase-architecture.yml` is a
working **envelope** instance; the prompt + publish seam it calls live in the
fetched-fresh harness (`harness/prompts/improve-codebase-architecture.md`,
`harness/cli.py`). Copy the envelope, change only the skill path and label if
porting to another repo. Note the home-repo envelope reads `harness/` straight
from its own `ref: main` checkout; a downstream repo clones `dividedby/skills`
into a temp dir for it — see [`proposal-loop-harness.md`](./proposal-loop-harness.md).

## To propagate to another repo

1. Copy the workflow envelope (it clones the harness fresh; nothing else to vendor).
2. Ensure the `CLAUDE_CODE_OAUTH_TOKEN` secret exists.
3. (Recommended) add a `CONTEXT.md` + `docs/adr/` so proposals speak the repo's
   own language.
4. `workflow_dispatch` once to verify it files ≤1 issue (or skips), then let the
   cron take over.

A repo can run **both** this loop and the
[Consumer loop](./consumer-setup.md) — they are independent jobs with separate
provenance labels, sharing only the harness.
