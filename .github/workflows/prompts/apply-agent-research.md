# Scheduled apply-agent-research pass

You are running unattended in GitHub Actions. No user is watching. Do not ask
questions — make the call yourself. Your job is to apply the `apply-agent-research`
skill to **this** repo and file **at most one issue per channel**, or none (see
`docs/adr/0011-per-channel-proposal-caps.md`).

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

2. **Gather candidates per channel** (each with a stable `dedup_key`, an integer
   `priority`, and a drafted title/body). These are **separate channels**, each
   capped independently — not one shared slot:
   - **Self-improvement** — a KB practice that sharpens a weak agent-meta surface
     here (a `CLAUDE.md` rule, a hook/setting, a CI workflow, or an existing skill)
     that the repo does not already encode.
   - **Skills on general merit** — a KB practice broadly useful enough to warrant a
     net-new published skill (ADR 0001), not just a refinement.
   - **Drain `skill-request` issues** — `gh issue list --label skill-request --state open`;
     fold the best-supported request into a proposed skill. Duplicate requests are
     corroborating demand, not noise.

   This repo has **no local (non-published) skills**, so the `skill-audit` channel
   is inert here — skip it. Incoming **`skill-promotion`** offers are human-actionable
   issues (a Consumer offering a local skill it built); the workflow ensures that
   label exists, but you do **not** drain them into a candidate — leave them for the
   maintainer to adopt (see `docs/design/skill-promotion-flow.md`).

3. **Pick and guard one best candidate _per channel_.** For each channel above,
   run the one-proposal gate over **only that channel's** candidates (and the keys
   already open in that channel), exactly as `proposal-flow.md` describes. Run each
   chosen candidate's final `title + body` through the leak guard first. Here
   `<skill-dir>` is `skills/meta/apply-agent-research`, so the calls are
   `python3 skills/meta/apply-agent-research/lib/cli.py sanitize` then `... gate`,
   run from the repo root. If the guard blocks, revise the body to drop the
   structural trigger and re-check — do not bypass it. The skills repo is public and
   has no private markers to pass.

4. **File or skip, per channel.** For each channel whose gate returns a candidate,
   `gh issue create` it with `--label source:agent-research`, ending the body with
   the `dedup-key` marker and a short Sources line citing the knowledge note(s).
   For each channel that returns nothing, print `SKIPPED: <channel>: <reason>`.
   **At most one issue per channel. Zero is acceptable** — a forced finding is worse
   than none.

## Rules

- **Read-only on this repo. No commits, no edits, no PRs.** The only mutation
  allowed is `gh issue create` with the provenance label (plus `gh label create`,
  which the workflow already ran). The skill writes nothing to the tree.
- Read-only on the mirror; never write back to it or to agent-research.
- At most one issue per channel. No questions. There is no user.
