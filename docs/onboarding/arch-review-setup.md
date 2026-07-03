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
- **Cadence:** 3×/week (Mon/Wed/Sat), in the shared **Mon/Wed/Sat window** — slot the cron by
  the harness hash rule (`sha1("{repo}/improve-codebase-architecture")` within the
  `* * 1,3,6` band). It has no corpus input, so it only needs to avoid
  colliding with the other loops' minutes, which the hash gives for free.
- **Input:** none to fetch — the input *is* the checked-out repo. The skill reads
  `CONTEXT.md` + `docs/adr/` for domain language; without them it still runs, just
  blind to the repo's vocabulary.
- **Split prompt: fetched-fresh skeleton + fetched depth rubric + local Repo-context include**
  ([ADR 0016](../adr/0016-arch-review-prompt-is-skeleton-plus-local-repo-context-include.md),
  [ADR 0020](../adr/0020-arch-review-fetches-depth-rubric-fresh-and-adds-simplification-legibility-lenses.md)).
  Unlike `apply-agent-research`'s single env-parametrized prompt, this loop's
  per-repo variation *is content* — what to review, which disciplines bind — which
  has no env representation. So the prompt is three parts joined by the reusable body:
  - The **skeleton** (`harness/prompts/improve-codebase-architecture.md`, fetched
    fresh) carries everything shared: the unattended/publish-seam framing, the
    three-lens structure (simplification, depth, legibility), the proposal
    discipline (Task steps 1–6), and the lockstep `<output>`/`<body>` schema. It
    is **scope-free** and does not model the depth concepts — it forward-references
    the depth rubric appended below.
  - The **depth rubric** (`mattpocock/skills` → `codebase-design/SKILL.md` +
    `codebase-design/DEEPENING.md`, written as `depth-LANGUAGE.md` /
    `depth-DEEPENING.md` for reusable-body compatibility) carries the depth
    concepts: deep/shallow modules, seams, and the deletion test. Clone-first
    (#525): the workflow clones `mattpocock/skills` one step earlier (to install
    the skill) and runs `python3 harness/cli.py fetch-rubric --out-dir
    "$RUNNER_TEMP" --source-dir "$MATTPOCOCK_SKILLS"` to read both files from
    that local clone — no separate network call. (A consumer still pinned at the
    `claude-loops-v1` tag from before #525 calls `fetch-rubric` without
    `--source-dir`; the CLI falls back to the old network fetch for it until the
    tag moves — a transitional lane tracked for removal in #523/#516.) Either
    lane **hard-fails the run if either file is missing/unfetchable** (ADR 0020
    c) — an unattended run with a missing rubric would produce unsound depth
    proposals. The upstream paths (and, for the legacy lane, URLs) live once in
    `harness/cli.py`; a future path change is a one-line fix there. The rubric
    floats at `main` (no SHA pin on the clone): consumers automatically track
    mattpocock's latest depth thinking, and an upstream rename or deletion
    surfaces immediately as a hard-fail rather than silently drifting (ADR 0020 b).
    **Supply-chain implication:** a third-party maintainer's changes enter this
    loop's unattended runs unreviewed each week. This is a deliberate choice made
    by the `dividedby/skills` maintainer; consumers who want review-before-run
    should pin a SHA in the reusable body.
  - The **include** (`.github/arch-review-context.md`, vendored per repo) carries
    the irreducibly repo-specific substance: primary/fallback/out-of-scope review
    scope and the binding disciplines/ADRs (plus any repo-specific emit hints). It
    names its own path so the agent knows it is editable.
  - The **reusable body concatenates** all three into the system prompt (skeleton →
    labeled depth rubric → repo-context include). The agent never consumes these
    paths directly — the reusable body does the concatenation.
  - **A missing include or failed rubric fetch hard-fails the run.** The reusable body
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
    without any local changes. Step 5's body-drafting rules also instruct the agent
    to include a **Design-tension section** per proposal — naming 2–3
    candidate-specific competing constraints with a sketch under each and a tension
    statement the human must resolve at triage — an async adaptation of the
    DESIGN-IT-TWICE principle inlined at principle level (ADR 0020, second
    amendment).
- **No cross-repo writes**, so **no `ISSUES_TOKEN`** — only
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
  the one-proposal-per-run cap and the provenance label live **in code**, not in
  prompt-adherence, and a missing/garbled block **fails the run loudly** rather
  than skipping silently. It is a *tested stdlib parser*, replacing the brittle
  `sed`/`jq` hand-escaping that caused #117/#211. It writes the step summary
  (outcome + candidates considered) itself; an `if: failure()` step surfaces the
  raw log when it fails. This is the generator/publisher split adapted from
  `mattpocock/course-video-manager`'s `architecture-review.yml`; the harness gives
  us in tested Python what it gets from the sandcastle framework.
- **Tools (read-only `gh` + read-only `git`):**
  `Bash(gh issue list:*) Bash(gh issue view:*) Bash(git log:*) Bash(git diff:*) Bash(git show:*) Bash(git blame:*) Bash(git ls-files:*) Bash(git status:*) Read Grep Glob`.
  No `WebSearch`/`WebFetch` — the depth rubric is fetched by the shell step above
  (not the model), so web access would only add an exfil surface for injected
  prompts. The agent gets only read access to the tracker — it *cannot*
  `gh issue create`, which makes the deterministic publish the sole filing path.

## Reference

`dividedby/skills` → `.github/workflows/improve-codebase-architecture.yml` is the
**home-repo** thin caller stub; it calls the reusable body via local `./` (canary).
Consumer repos vendor a thin caller stub that pins `@claude-loops-v1` (#382):

```yaml
uses: dividedby/skills/.github/workflows/improve-codebase-architecture-reusable.yml@claude-loops-v1
secrets:
  CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

The stub carries no skill path, no label, no `claude -p` flags — all of that lives
in the reusable body (`improve-codebase-architecture-reusable.yml`), which clones
`dividedby/skills` fresh each run for the harness, the prompt skeleton, and the
skill. The **only per-repo piece a consumer must supply** is the
`.github/arch-review-context.md` include (the reusable body `test -f`s it and
hard-fails the run if it is missing). See
[`proposal-loop-harness.md`](./proposal-loop-harness.md) for the canonical
thin-stub form (both home-repo `./` and consumer `@claude-loops-v1` variants).

## Second opinions are interactive, not in-loop

A multi-agent `/council` panel is **deliberately not** wired into this scheduled
loop — the per-run cost (7–12×) breaks the loop's sonnet pin + `--max-budget-usd`
backstop, and the in-session `Workflow` primitive it needs is the wrong tool for
headless cron (spike [#495](https://github.com/dividedby/skills/issues/495);
rationale in [`.out-of-scope/council-in-scheduled-arch-loop.md`](../../.out-of-scope/council-in-scheduled-arch-loop.md)).
For a high-stakes proposal, invoke `/council` **interactively at triage** on the
filed `source:architecture-review` issue before acting — pay-per-use, only on the
proposals worth it.

## To propagate to another repo

1. Vendor the thin caller stub: create
   `.github/workflows/improve-codebase-architecture.yml` in the target repo with
   `on: schedule` (derive the cron slot with the hash-stagger rule in
   [`proposal-loop-harness.md`](./proposal-loop-harness.md)) + `workflow_dispatch`,
   and the `permissions:` / `uses:` / `secrets:` block shown in "Reference" above.
   No skill path, no label, no `claude -p` flags — those live in the reusable body.
2. **Write your repo's `.github/arch-review-context.md` include** — the one file
   you must vendor. Give it your primary/fallback/out-of-scope review scope and
   the disciplines/ADRs the loop must respect; have it name its own path so the
   agent knows it is editable. Without it the run hard-fails on the reusable
   body's `test -f`. Use this repo's include as a template.
3. Ensure the `CLAUDE_CODE_OAUTH_TOKEN` secret exists.
4. (Recommended) add a `CONTEXT.md` + `docs/adr/` so proposals speak the repo's
   own language.
5. `workflow_dispatch` once to verify it files ≤1 issue (or skips), then let the
   cron take over.

A repo can run **both** this loop and the
[Consumer loop](./consumer-setup.md) — they are independent jobs with separate
provenance labels, sharing only the harness.
