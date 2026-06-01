# Onboard a repo with the architecture-review loop

This stands up `improve-codebase-architecture` as a scheduled
[proposal loop](./proposal-loop-harness.md) in any repo with code worth
reviewing. It is the **simplest** member of the family: the
[harness](./proposal-loop-harness.md) plus a skill, with **no** knowledge-mirror
input and **no** cross-repo channels. It reads the codebase itself — informed by
`CONTEXT.md` + `docs/adr/` if present — and files refactor proposals into the
repo's own tracker. **Read the harness doc first**; this doc is only the deltas.

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
- **Tools:** `Bash(gh:*) Bash(git:*) Read Grep Glob WebSearch WebFetch`.

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
