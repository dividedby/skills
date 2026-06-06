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
- **Deterministic publish, structured `<output>`.** The agent does **not** file
  the issue. It explores, decides, and ends its run with a single schema-validated
  `<output>` JSON block (`status: proposed|skipped`, plus `title` / `body` /
  `oneLineSummary` / `candidatesConsidered`, or `reason`). A `Publish proposal`
  shell step parses that block and runs `gh issue create` itself — so the
  one-proposal-per-run cap and the provenance label live **in code**, not in
  prompt-adherence, and a missing/garbled block **fails the run loudly** rather
  than skipping silently. The step summary surfaces the outcome + candidates
  considered. This is the generator/publisher split adapted from
  `mattpocock/course-video-manager`'s `architecture-review.yml`; we hand-roll in
  shell what it gets from the sandcastle framework.
- **Tools (read-only `gh`):**
  `Bash(gh issue list:*) Bash(gh issue view:*) Bash(gh search:*) Bash(gh api:*) Bash(git:*) Read Grep Glob WebSearch WebFetch`.
  The agent gets only read access to the tracker — it *cannot* `gh issue create`,
  which makes the deterministic publish the sole filing path.

## Reference

`dividedby/skills` → `.github/workflows/improve-codebase-architecture.yml` +
`.github/workflows/prompts/improve-codebase-architecture.md` is a working
instance — copy it, change only the skill path and label if porting to another
repo.

## To propagate to another repo

1. Copy the workflow + its prompt.
2. Ensure the `CLAUDE_CODE_OAUTH_TOKEN` secret exists.
3. (Recommended) add a `CONTEXT.md` + `docs/adr/` so proposals speak the repo's
   own language.
4. `workflow_dispatch` once to verify it files ≤1 issue (or skips), then let the
   cron take over.

A repo can run **both** this loop and the
[Consumer loop](./consumer-setup.md) — they are independent jobs with separate
provenance labels, sharing only the harness.
