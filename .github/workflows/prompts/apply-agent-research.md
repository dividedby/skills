# Weekly apply-agent-research pass

You are running unattended in GitHub Actions. No user is watching. Do not ask
questions — make the call yourself. Your job is to apply the `apply-agent-research`
skill to **this** repo and file **at most one** issue, or none.

Invoke the in-repo skill `skills/meta/apply-agent-research/SKILL.md` and follow it;
this prompt is the concrete wiring for the skills-repo instance. Read both the
`SKILL.md` and its `proposal-flow.md` before acting.

## Inputs (already prepared / where to read)

- **Knowledge mirror:** already shallow-cloned at `$MIRROR_DIR` (read-only). Read
  `$MIRROR_DIR/knowledge/<subject>/{practices,artifacts}/index.md` first, then the
  concept files each index points to. Do **not** clone the private agent-research.
- **This repo's own governance docs:** `CONTEXT.md`, `CLAUDE.md`, every file under
  `docs/adr/`, and the skills under `skills/<bucket>/`. Use them as the ethos-fit
  oracle *and* the already-do-this filter (per the skill). Treat ADRs as binding.

## Task

1. **Recover what's already been proposed.** List prior proposals so you do not
   re-file one:

   ```
   gh issue list --label source:agent-research --state all --limit 100
   ```

   Read their bodies for the `<!-- dedup-key: ... -->` markers and read the
   comments on closed ones — the maintainer's pushback is your calibration signal.
   Any key that is **open** or was closed as **`wontfix`** is spoken for; collect
   those keys for the gate's `open_issues`.

2. **Gather candidates** (each with a stable `dedup_key`, an integer `priority`,
   and a drafted title/body):
   - **Self-improvement** — a KB practice that sharpens a weak agent-meta surface
     here (a `CLAUDE.md` rule, a hook/setting, a CI workflow, or an existing skill)
     that the repo does not already encode.
   - **Skills on general merit** — a KB practice broadly useful enough to warrant a
     net-new published skill (ADR 0001), not just a refinement.
   - **Drain `skill-request` issues** — `gh issue list --label skill-request --state open`;
     fold the best-supported request into a proposed skill. Duplicate requests are
     corroborating demand, not noise.

3. **Pick and guard the single best candidate.** Run its final `title + body`
   through the leak guard, then the one-proposal gate, exactly as
   `proposal-flow.md` describes. Here `<skill-dir>` is
   `skills/meta/apply-agent-research`, so the calls are
   `python3 skills/meta/apply-agent-research/lib/cli.py sanitize` then `... gate`,
   run from the repo root. If the guard blocks, revise the body to
   drop the structural trigger and re-check — do not bypass it. The skills repo is
   public and has no private markers to pass.

4. **File or skip.** If the gate returns a candidate, `gh issue create` it with
   `--label source:agent-research`, ending the body with the `dedup-key` marker and
   a short Sources line citing the knowledge note(s). If the gate returns nothing,
   print `SKIPPED: <one-line reason>` and stop. **One issue per run, maximum. Zero
   is acceptable** — a forced finding is worse than none.

## Rules

- **Read-only on this repo. No commits, no edits, no PRs.** The only mutation
  allowed is `gh issue create` with the provenance label (plus `gh label create`,
  which the workflow already ran). The skill writes nothing to the tree.
- Read-only on the mirror; never write back to it or to agent-research.
- One issue per run, maximum. No questions. There is no user.
