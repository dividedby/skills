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
- **Cadence:** weekly, in the shared **Friday-evening window** — slot the cron by
  the harness hash rule (`sha1("{repo}/improve-codebase-architecture")` within the
  Saturday-UTC `* * 6` band). It has no corpus input, so it only needs to avoid
  colliding with the other loops' minutes, which the hash gives for free.
- **Input:** none to fetch — the input *is* the checked-out repo. The skill reads
  `CONTEXT.md` + `docs/adr/` for domain language; without them it still runs, just
  blind to the repo's vocabulary.
- **Split prompt: fetched-fresh skeleton + fetched depth rubric + local Repo-context include**
  ([ADR 0016](../adr/0016-arch-review-prompt-is-skeleton-plus-local-repo-context-include.md),
  [ADR 0020](../adr/0020-arch-review-fetches-depth-rubric-fresh-and-adds-simplification-legibility-lenses.md)).
  Unlike `apply-agent-research`'s single env-parametrized prompt, this loop's
  per-repo variation *is content* — what to review, which disciplines bind — which
  has no env representation. So the prompt is three parts joined by the envelope:
  - The **skeleton** (`harness/prompts/improve-codebase-architecture.md`, fetched
    fresh) carries everything shared: the unattended/publish-seam framing, the
    three-lens structure (simplification, depth, legibility), the proposal
    discipline (Task steps 1–6), and the lockstep `<output>`/`<body>` schema. It
    is **scope-free** and does not model the depth concepts — it forward-references
    the depth rubric appended below.
  - The **depth rubric** (`mattpocock/skills` → `LANGUAGE.md` + `DEEPENING.md`,
    fetched fresh from `main` at run time) carries the depth concepts: deep/shallow
    modules, seams, and the deletion test. The workflow fetches these files in a
    dedicated step before invoking the agent and **hard-fails the run if either
    fetch fails** — an unattended run with a missing rubric would produce unsound
    depth proposals. The rubric floats at `main` (no SHA pin): consumers
    automatically track mattpocock's latest depth thinking, and an upstream rename
    or deletion surfaces immediately as a hard-fail rather than silently drifting.
    **Supply-chain implication:** a third-party maintainer's changes enter this
    loop's unattended runs unreviewed each week. This is a deliberate choice made
    by the `dividedby/skills` maintainer; consumers who want review-before-run
    should pin a SHA in the envelope.
  - The **include** (`.github/arch-review-context.md`, vendored per repo) carries
    the irreducibly repo-specific substance: primary/fallback/out-of-scope review
    scope and the binding disciplines/ADRs (plus any repo-specific emit hints). It
    names its own path so the agent knows it is editable.
  - The **envelope concatenates** all three into the system prompt (skeleton →
    labeled depth rubric → repo-context include). The agent never consumes these
    paths directly — the envelope does the concatenation.
  - **A missing include or failed rubric fetch hard-fails the run.** The envelope
    `test -f`s `.github/arch-review-context.md` before invoking the agent, exactly
    like the existing `test -f …/SKILL.md` gate. Scope is load-bearing: a
    scope-free skeleton reviews blindly, so adopting this loop *requires* shipping
    the include. (This removes the harness's graceful degradation when a repo lacks
    `CONTEXT.md` — an intentional trade.)
  - **Self-edit affordance is local-only:** the agent may propose edits to its own
    in-repo files including the include, but **not** the upstream-owned skeleton or
    the fetched depth rubric (this loop has no channel to file against
    `dividedby/skills` or `mattpocock/skills`).
  - **Three lenses ship to all consumers via the shared skeleton.** The
    simplification lens (delete/stdlib/native/yagni/shrink) and the legibility lens
    (oversized files, non-conventional names, greppability, CLI surfacing) are
    modeled in the skeleton at principle level; the depth lens is forward-referenced
    to the fetched rubric. Every consumer of this skeleton gets all three lenses
    without any local changes.
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
  parses the JSON, copies each `<body-N>` verbatim, and runs `gh issue create` — so
  the five-proposals-per-run cap and the provenance label live **in code**, not in
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
5. `workflow_dispatch` once to verify it files ≤5 issues (or skips), then let the
   cron take over.

A repo can run **both** this loop and the
[Consumer loop](./consumer-setup.md) — they are independent jobs with separate
provenance labels, sharing only the harness.
