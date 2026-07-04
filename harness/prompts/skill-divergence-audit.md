# Scheduled skill-divergence-audit pass

You are running unattended in GitHub Actions. No user is watching. Do not ask
questions — make the call yourself. Your job is to apply the
`skill-divergence-audit` skill to **this** repo (`dividedby/skills`) and file
**at most one** `source:skill-audit` issue per run — usually none (see ADR
0019 in this repo). One is a ceiling, not a target.

This repo is both the tracker and the skill catalog under audit — unlike
`apply-agent-research`, there is no host/consumer branch here. **Never
hardcode the skill's mechanics in this prompt** — invoke the installed skill
at `$SKILL_DIR/SKILL.md` and follow it exactly; this prompt only supplies the
concrete wiring (paths, tool constraints) so the skill file stays the single
source of truth for the classify/gate/file steps.

## Inputs (env the workflow exports — read, do not guess)

- **`$MATTPOCOCK_SKILLS`** — a fresh `mattpocock/skills` clone (Step 1.2 of
  the skill). Read `skills/*/*/SKILL.md` under it the same way you read your
  own.
- **`$MIRROR_DIR`** — the public `agent-research-knowledge` mirror clone
  (Step 1.3 of the skill), read-only. Read
  `$MIRROR_DIR/knowledge/<subject>/{practices,artifacts}/index.md` first,
  then the concept files each index points to.
- **`$SKILL_DIR`** — the installed skill (`skills/meta/skill-divergence-audit`
  in this same checkout). Every skill/CLI call goes through it:
  `python3 $SKILL_DIR/lib/cli.py {gate,file}`. It resolves the sibling
  `apply-agent-research/lib/` (sanitizer + proposal_gate) itself — you never
  need to reference that path directly.
- **This repo's own** `skills/*/*/SKILL.md` (your own catalog), `CONTEXT.md`,
  and `docs/adr/`. Treat ADRs as binding, especially
  [ADR 0024](../../docs/adr/0024-lean-on-upstream-skills-soft-depend-over-reinvent.md)
  (soft-depended skills are an intentional gap, not a finding) and
  [ADR 0003](../../docs/adr/0003-skill-improvement-workflows-propose-via-issues.md)
  (propose via issues, never edit).

**Environment variable constraint:** do NOT inspect environment variables via
`printenv`, `env`, `python3 -c "import os; …"`, `cat /proc/*/environ`, or shell
`$VAR` expansion — these are denied by the sandbox allowlist. The three paths
above are already given to you in the task prompt.

**Tool-use constraint:** your only shell commands are
`gh issue list --label source:skill-audit --state all --limit 100` and
`gh issue view <n> --comments` (dedup against prior proposals — a `wontfix`
close is durable suppression), the read-only git set (`git log`, `git diff`,
`git show`, `git ls-files`, `git status`), and
`python3 $SKILL_DIR/lib/cli.py {gate,file}` (the guarded seam — see Filing
below). Everything else is `Read`, `Grep`, `Glob`, `Write`. Batch idioms are
denied: a `for`/`while` loop, `bash -c`, or a piped command is matched as one
opaque string, not its allowlisted parts — with one sanctioned exception: the
`printf '%s' '<json>' | python3 $SKILL_DIR/lib/cli.py gate` pipe (step 5
below); `Bash(printf:*)` is allowlisted precisely for it. Every other pipe,
`cat`, `echo`/`tee` redirection, and `python3 -c` are denied — use `Read` /
`Write` instead. Make one singular allowlisted call per item, never a loop.
**Quoting:** invoke `$SKILL_DIR/lib/cli.py` **unquoted**
(`python3 $SKILL_DIR/lib/cli.py gate`, no surrounding quotes around the path)
— the allowlist matches a literal prefix against the resolved path; quoting
it changes the string and gets denied (see #527).

## Task

Follow `$SKILL_DIR/SKILL.md` step by step:

1. **Scan** — enumerate this repo's `skills/*/*/SKILL.md`, `$MATTPOCOCK_SKILLS`'s
   skills, and `$MIRROR_DIR`'s KB index entries into three flat lists
   (name + pillars).
2. **Classify** — call `divergence.diff(our_skills, upstream_skills)` from
   `$SKILL_DIR/lib/divergence.py`. Do not re-derive the classification in
   prose.
3. **Render** — call `divergence.render_report(divergences)` and print it, for
   the record.
4. **Adversarial pre-gate** — before any candidate reaches the proposal gate,
   challenge it on the five rejection criteria in
   [`skills/meta/apply-agent-research/proposal-flow.md`](../../skills/meta/apply-agent-research/proposal-flow.md#the-proposal-gate--run-once-over-every-channels-candidates)
   (catalog overlap, restatement dilution, frequency fit, evidence strength,
   concreteness). A candidate that cannot clear all five is dropped before the
   gate sees it.
5. **Gate once** — recover prior `source:skill-audit` dedup keys via the
   `gh issue list` command above (open **and** `wontfix`-closed are
   spoken-for), call `divergence.to_candidates(divergences)`, then run the
   gate exactly once:
   `printf '%s' '<json>' | python3 $SKILL_DIR/lib/cli.py gate` with
   `"budget": 1`.
6. **File (or skip)** — for the single candidate the gate returns (if any),
   write the issue body via the `Write` tool (dedup-key HTML comment + a
   Sources line citing the upstream skill/KB note), then file through the
   guarded shim:

   ```
   python3 $SKILL_DIR/lib/cli.py file \
     --title "<concise title>" \
     --body-file <path> \
     --label source:skill-audit
   ```

   `file` sanitizes `title + body` and runs `gh issue create` only on ALLOW.
   Never call `gh issue create` directly — it is disallowed by the workflow's
   tool policy, and the skill is never granted that tool.

Reality gate: any claim about how a tool, flag, API, or upstream skill behaves
counts as verified only if you can quote it from `$MATTPOCOCK_SKILLS`,
`$MIRROR_DIR`, or this repo in-session — not recalled from memory. Fabricating
or approximating a quote disqualifies the candidate.

End your run with a one-line summary: the filed issue URL, or
`SKIPPED: <reason>` (e.g. "every candidate already covered by a prior
source:skill-audit proposal", "nothing cleared the adversarial pre-gate").

## Rules

- **Read-only on this repo, `$MATTPOCOCK_SKILLS`, and `$MIRROR_DIR`.** No
  commits, no edits, no PRs, no writes to either clone. The only mutation is
  filing through the guarded `cli.py file` path (own tracker, own
  `source:skill-audit` label — already exists, never create a new one).
- **`ALIGNED` and `NO_UPSTREAM_EQUIVALENT` are report-only.** Surface them in
  the rendered report; never pass them to `to_candidates` or file them.
- **Soft-dependency skills are not gaps.** `divergence.py`'s
  `SOFT_DEPENDENCY_SKILLS` set already excludes the deliberately-deleted
  mattpocock skills this repo soft-depends on (ADR 0024) from
  `MISSING_HERE` — do not manually re-flag one of those names.
- At most one issue per run, gate-enforced; one is a ceiling, not a target. A
  forced finding is worse than none. No questions. There is no user.
