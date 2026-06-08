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
- **Split prompt: fetched-fresh skeleton + local Repo-context include**
  ([ADR 0016](../adr/0016-arch-review-prompt-is-skeleton-plus-local-repo-context-include.md)).
  Unlike `apply-agent-research`'s single env-parametrized prompt, this loop's
  per-repo variation *is content* — what to review, which disciplines bind — which
  has no env representation. So the prompt is two parts joined by the envelope:
  - The **skeleton** (`harness/prompts/improve-codebase-architecture.md`, fetched
    fresh) carries everything shared: the unattended/publish-seam framing, the
    proposal discipline (Task steps 1–6), and the lockstep `<output>`/`<body>`
    schema. It is **scope-free** — its `## Scope` section forward-references the
    appended Repo-context block.
  - The **include** (`.github/arch-review-context.md`, vendored per repo) carries
    the irreducibly repo-specific substance: primary/fallback/out-of-scope review
    scope and the binding disciplines/ADRs (plus any repo-specific emit hints). It
    names its own path so the agent knows it is editable.
  - The **envelope concatenates** them into the system prompt:
    `--append-system-prompt "$(cat harness/prompts/improve-codebase-architecture.md; printf '\n\n'; cat .github/arch-review-context.md)"`.
    The agent never consumes the include's path itself — the envelope does the
    concatenation — which is why the path is a fixed convention, **not** an env var.
  - **A missing include hard-fails the run.** The envelope `test -f`s
    `.github/arch-review-context.md` before invoking the agent, exactly like the
    existing `test -f …/SKILL.md` gate. Scope is load-bearing: a scope-free
    skeleton reviews blindly, so adopting this loop *requires* shipping the
    include. (This removes the harness's graceful degradation when a repo lacks
    `CONTEXT.md` — an intentional trade.)
  - **Self-edit affordance is local-only:** the agent may propose edits to its own
    in-repo files including the include, but **not** the upstream-owned skeleton
    (this loop has no channel to file against `dividedby/skills`).
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
working **envelope** instance; the scope-free skeleton + publish seam it calls
live in the fetched-fresh harness (`harness/prompts/improve-codebase-architecture.md`,
`harness/cli.py`), and its own scope lives in the local
`.github/arch-review-context.md` include. Copy the envelope, change the skill path
and label, and ship your own include if porting to another repo. Note the
home-repo envelope reads `harness/` straight from its own `ref: main` checkout; a
downstream repo clones `dividedby/skills` into a temp dir for it — see
[`proposal-loop-harness.md`](./proposal-loop-harness.md).

## To propagate to another repo

1. Copy the workflow envelope (it clones the harness fresh).
2. **Write your repo's `.github/arch-review-context.md` include** — the one file
   you must vendor. Give it your primary/fallback/out-of-scope review scope and
   the disciplines/ADRs the loop must respect; have it name its own path so the
   agent knows it is editable. Without it the run hard-fails on the envelope's
   `test -f`. Use this repo's include as a template.
3. Ensure the `CLAUDE_CODE_OAUTH_TOKEN` secret exists.
4. (Recommended) add a `CONTEXT.md` + `docs/adr/` so proposals speak the repo's
   own language.
5. `workflow_dispatch` once to verify it files ≤1 issue (or skips), then let the
   cron take over.

A repo can run **both** this loop and the
[Consumer loop](./consumer-setup.md) — they are independent jobs with separate
provenance labels, sharing only the harness.
