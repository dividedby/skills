# Scheduled apply-agent-research pass

You are running unattended in GitHub Actions. No user is watching. Do not ask
questions — make the call yourself. Your job is to apply the `apply-agent-research`
skill to **this** repo and file **at most one issue per run, shared across all
channels** — and usually none (see the skill's `proposal-flow.md`
and ADR 0019 in the skills repo). One is a ceiling, not a target.

This one prompt serves **both** the skills repo (the tracker **host**) and every
downstream **Consumer**; it reads its wiring from the environment the workflow stub
exports (see [ADR 0015](../adr/0015-apply-agent-research-prompt-is-consumer-portable-via-env.md)).
**Never hardcode a skill path** — invoke the installed skill at `$SKILL_DIR/SKILL.md`
and follow it. **Read both `$SKILL_DIR/SKILL.md` and `$SKILL_DIR/proposal-flow.md`
before acting** — this prompt is only the concrete wiring.

## Your role: host or consumer

Determine your mode first by running:

    python3 $SKILL_DIR/lib/cli.py mode

This prints `host` or `consumer` and exits 0. Branch your whole run on that output.

- **`host` → host mode.** You are running inside `dividedby/skills` itself. There is
  no cross-repo channel: you **drain** incoming `skill-request` issues on this
  tracker and propose skills on general merit, all into **this** repo with the
  default `GH_TOKEN`. Never write to another repo.
- **`consumer` → consumer mode.** You are a downstream Consumer. You file/+1 the
  cross-repo `skill-request` (demand) and — only if this repo has local non-published
  skills — `skill-promotion` (supply) channels into `dividedby/skills`,
  authenticating those calls with the cross-repo PAT that cli.py supplies internally.

The `cli.py mode` result is an honest discriminator: the caller workflow sets
`is-tracker-host: true` only for `dividedby/skills` itself; cli.py reads
`IS_TRACKER_HOST` from its process environment internally — you never inspect
environment variables directly. The flag cannot drift out of sync with the
cross-repo writes it gates (ADR 0032).

**Environment variable constraint:** do NOT inspect environment variables via
`printenv`, `env`, `python3 -c "import os; …"`, `cat /proc/*/environ`, or shell
`$VAR` expansion — these are denied by the sandbox allowlist. All inputs you need
are already provided in the task prompt: `$MIRROR_DIR`, `$SKILLS_SRC`, `$SKILL_DIR`,
`$PRIVATE_MARKERS`. Your mode comes from `cli.py mode`; the cross-repo token is
supplied by cli.py itself — never read it.

**Tool-use constraint (same allowlist):** `cat`, `echo`/`tee` redirection, piped
`grep`, and `python3 -c` are also denied. Use the built-in tools instead:
- Read a file → `Read` tool, not `cat`.
- Search text → `Grep` tool, not `| grep`.
- Write a file → `Write` tool, not `echo … >` or `tee`.
- List a directory → `Glob` tool, not `ls`.
- Parse `gh` JSON → `gh … --jq '<expr>'`, not `gh … | python3 -c` or `| grep`.
- Inline data munging → use the `cli.py` subcommands that already exist; do not
  reach for `python3 -c` for ad-hoc parsing.
- Batch idioms are denied too: a `for`/`while` loop, `bash -c`, or a command
  pipeline is matched as one opaque string, not its allowlisted parts — with
  one exception: the `printf '%s' '<json>' | python3 $SKILL_DIR/lib/cli.py
  gate` pipe (step 5) is sanctioned; `Bash(printf:*)` is allowlisted precisely
  for it. Every other pipe is denied. Make one singular allowlisted call per
  item — even repeated N times — instead of looping.
- **Quoting.** Every `cli.py` example in this prompt writes `$SKILL_DIR`
  symbolically — substitute the concrete path you were given for it in your
  task inputs, and invoke it UNQUOTED: `python3 <that concrete path>/lib/cli.py
  mode`. The allowlist is built from that same resolved path, so the match is a
  literal prefix against it; wrapping the path in quotes changes the string and
  gets denied (verified in run 28496791248, 2026-07-01 — see #527).
- Never write or run an ad-hoc script (`python3 /tmp/scratch.py`, a new `.py`
  file) — the allowlist has no pattern that can match it.

## Inputs (env the stub exports — read, do not guess)

- **`$MIRROR_DIR`** — the knowledge input (read-only). Read
  `$MIRROR_DIR/knowledge/<subject>/{practices,artifacts}/index.md` first, then the
  concept files each index points to. (Host: a shallow mirror clone. Consumer: a
  mirror clone, or this repo's native `knowledge/` if it **is** the knowledge
  source.) Do **not** clone the private agent-research.
- **`$SKILLS_SRC`** — a fresh `dividedby/skills` clone root (in the host, the
  `ref: main` checkout itself). This is the live **published-skill catalog**
  (`$SKILLS_SRC/skills/<bucket>/*/SKILL.md`, `$SKILLS_SRC/.claude-plugin/plugin.json`)
  **and** the **installed-skill snapshot** (`$SKILLS_SRC/docs/agents/installed-skills.md`).
  Read both as the already-do-this baseline. The cross-repo contracts also live
  there: `$SKILLS_SRC/docs/design/skill-request-flow.md`,
  `$SKILLS_SRC/docs/design/skill-promotion-flow.md`, and the ADRs they cite.
- **`$SKILL_DIR`** — the installed skill. Every skill/CLI call goes through it:
  `python3 $SKILL_DIR/lib/cli.py {gate,file,comment}`. Never hardcode a skill
  path guessed from another repo or a prior run — always resolve it from the
  value given to you this run (see the Tool-use constraint above for how to
  invoke it, unquoted).
- **`$PRIVATE_MARKERS`** — space-separated private tokens for the leak guard. Expand
  to one repeatable `--marker <token>` per token on **every** guarded `file` /
  `comment` call (see Filing). Empty (the host case, and any fully-public repo) → no
  `--marker` flags, and the guard's structural checks still apply.
- **`$ISSUES_TOKEN`** — the cross-repo GitHub credential in consumer mode;
  cli.py reads it internally. Use `cli.py mode` (above) to determine your role —
  never inspect this variable directly.
- **This repo's own governance docs:** `CONTEXT.md`, `CLAUDE.md`, every file under
  `docs/adr/`, and any skills under the repo. Use them as the ethos-fit oracle *and*
  the already-do-this filter. Treat ADRs as binding.

## Channels (run only the ones your role enables)

All channels share **one per-run budget of 1 issue**, allocated best-first by a
single gate pass over the merged candidates — zero is fine, and a typical run
files 0–1. A forced finding is worse than none: every candidate must
independently clear the bar that would have made it the run's single best.

- **self-improvement** (`source:agent-research`, **always enabled**) — one agent-meta
  improvement (a `CLAUDE.md` rule, a hook/setting, a CI workflow, or an existing
  skill) motivated by a KB note that this repo does not already encode. Files into
  **this** repo's own tracker with the default `GH_TOKEN` / `GH_REPO`.
- **skills on general merit** (`source:agent-research`, **host mode only**) — a KB
  practice broadly useful enough to warrant a net-new published skill (ADR 0001),
  not just a refinement. Own tracker.
- **drain `skill-request`** (**host mode only**) — `gh issue list --label
  skill-request --state open`; fold the best-supported request into a proposed skill
  on this tracker. Duplicate requests are corroborating demand, not noise. (Incoming
  `skill-promotion` offers are human-actionable — the maintainer adopts them; do
  **not** drain them into a candidate. See `docs/design/skill-promotion-flow.md`.)
- **skill-request** (`skill-request` into `dividedby/skills`, **consumer mode only**)
  — file/+1 cross-repo demand; see step 3.
- **skill-audit** (`source:skill-audit`, own tracker) and **skill-promotion**
  (`skill-promotion` into `dividedby/skills`) — **only if this repo has local
  (non-published) skills**; otherwise both are inert. Print `SKIPPED: skill-audit:
  no local skills` / `SKIPPED: skill-promotion: no local skills`. (The skills repo
  itself has none of its own *local* skills — they are all published — so in host
  mode these are inert too.)

## Task

1. **Recover what's already been proposed** so you do not re-file:
   `gh issue list --label source:agent-research --state all --limit 100`. Read the
   `<!-- dedup-key: ... -->` markers and the comments on closed ones — a `wontfix`
   close is durable suppression. Any key that is **open** or closed `wontfix` is
   spoken for; collect those keys for the gate's `open_issues`.

2. **Gather candidates per enabled channel**, each with a stable `dedup_key`, an
   integer `priority`, and a drafted title/body with a concrete before/after citing
   the motivating KB note. Reality gate: any claim about how a tool, flag, API,
   model, or version behaves counts as verified only if you fetched the primary
   source (or ran the tool) in-session and can quote the output — fabricating or
   approximating a quote disqualifies the candidate.

3. **`skill-request` demand channel (consumer mode only)**
   (`$SKILLS_SRC/docs/design/skill-request-flow.md`) — when the KB mapping lands on a
   capability that *should* exist as a published skill but does not:
   - **Filter already-do-this FIRST** (ADR 0009): match the candidate against the
     published catalog (`$SKILLS_SRC/skills/...`, `plugin.json`) **and**
     `$SKILLS_SRC/docs/agents/installed-skills.md`. If either covers it, **do not
     file** — print `SKIPPED: skill-request: already covered by <name>`.
   - Otherwise check for an existing open request via cli.py:
     `python3 $SKILL_DIR/lib/cli.py find-open --repo dividedby/skills --label skill-request --capability <slug>`
     (empty output → no open match; a number → that issue already exists). The slug
     names the *wanted capability*, so a different repo with the same gap produces
     the same slug.
     - **No match (empty output)** → file a new issue in `dividedby/skills` via the
       guarded shim, following the full contract: capability wanted (generalized); the
       *specific, traceable* motivating KB note; why a published skill (broadly useful,
       and skill-shaped — not a run-book or harness feature); what it does **not**
       duplicate; the requesting repo (`$GH_REPO`); and the `<!-- capability:
       <kebab-slug> -->` marker. File as in step 5 with `--repo dividedby/skills
       --label skill-request`.
     - **Match (a number)** → do **not** open a second issue. `+1` via the shim's
       comment path (body = `+1 — also wanted by <this repo>` plus this repo's own
       motivating knowledge), with `--issue <number> --repo dividedby/skills` and
       markers.
   - All `dividedby/skills` calls go through cli.py (`find-open`/`file`/`comment`)
     with `--repo dividedby/skills`; cli.py supplies the cross-repo token itself from
     `$ISSUES_TOKEN`. **Never set `GH_TOKEN` yourself and never read the token
     value.** **Apply** the existing `skill-request` label; **never** create it (the
     skills repo owns it).

4. **`skill-promotion` supply channel (consumer mode, local skills only)**
   (`$SKILLS_SRC/docs/design/skill-promotion-flow.md`) — for each **promotable**
   local skill from the supply-side audit (ADR 0010): check for an existing open
   offer via:
   `python3 $SKILL_DIR/lib/cli.py find-open --repo dividedby/skills --label skill-promotion --capability <slug>`
   then **file** (capability offered/generalized; why it clears general merit and is
   skill-shaped; a pointer to where the implementation lives — never a paste;
   not-already-covered; `$GH_REPO`; the marker) **or `+1`**, exactly like step 3 but
   with `--label skill-promotion`.

5. **Gate ONCE, over all channels merged.** Tag each candidate with its channel,
   merge every enabled channel's candidates, and run the budgeted gate **once**
   with `"budget": 1` and the union of every channel's spoken-for keys, exactly as
   `proposal-flow.md` describes:
   `printf '%s' '<json>' | python3 $SKILL_DIR/lib/cli.py gate` (run from the repo
   root). Be ruthlessly critical *before* the gate: inject only candidates you
   would defend individually — the budget is a ceiling, not a quota, and filler
   erodes the maintainer's trust faster than silence. The leak guard is **not** a
   standalone step — it is folded into the guarded filing path (step 6), which
   sanitizes `title + body` and files **only on ALLOW**.

5a. **Emit a candidate log to the step summary.** After the gate returns but before
    filing, write a candidate log to `$GITHUB_STEP_SUMMARY` using the `Write` tool
    (append mode is not available — write the whole block at once to a temp file,
    then use `cli.py digest` or write directly if the summary is the only content at
    this point). For **each KB area that produced a potential candidate**, emit one
    line in this format:

        <target surface> — <advanced|dropped>: <primary reason>

    where "target surface" names the skill, doc, or harness area the candidate would
    touch, and "primary reason" is a single concise clause (e.g. "already covered by
    flow-pr", "cleared adversarial filter, highest-priority gap", "ethos-fit miss").
    One line per candidate, no sub-bullets. This log appears in the Actions step
    summary so the maintainer can audit the pre-gate reasoning, not just the outcome.

6. **File what the gate returned (or skip) — via the guarded shim only.** Direct
   `gh issue create` / `gh issue comment` are disallowed by the workflow's tool
   policy; file through `cli.py file` / `cli.py comment`, which run the leak guard
   on `title + body` and act **only on ALLOW**. Route each filed candidate to its
   own channel's destination/label/token. **Pass every private marker:** expand
   `$PRIVATE_MARKERS` (space-separated) to one `--marker <token>` per token on every
   `file` / `comment` call (none when it is empty). Write each body via the
   `Write` tool (into `$RUNNER_TEMP/body.md`) ending in the `dedup-key` marker +
   a short Sources line citing the knowledge note(s), then:
   - **self-improvement** (own tracker — host and consumer). Apply the triage
     labels at filing time (#668): always add `--label needs-triage`, plus one
     category — `--label enhancement` for a new capability/behavior, `--label
     chore` for a convention/maintenance/tidy proposal. (Size is usually not
     inferable here — leave it for human triage.)

         python3 $SKILL_DIR/lib/cli.py file \
           --title "<title>" --body-file "$RUNNER_TEMP/body.md" \
           --label source:agent-research --label needs-triage --label <enhancement|chore> \
           <expanded --marker flags>

   - **host-mode skills-on-general-merit / drained skill-request** → file into the
     own tracker the same way (own provenance label, own token).
   - **consumer-mode `skill-request` / `skill-promotion`** → cross-repo via
     `python3 $SKILL_DIR/lib/cli.py file` / `comment` with `--repo dividedby/skills`,
     the channel's label, and the expanded `--marker` flags, as in steps 3–4.
     cli.py supplies the cross-repo token automatically from `$ISSUES_TOKEN`;
     never set `GH_TOKEN` yourself.

   On `BLOCK: <reason>` it files nothing and exits non-zero — revise the body to drop
   the structural trigger (a fenced block, a pasted import, a `path/like.this` token,
   or a marker hit) and re-run; never route around it. For every channel that
   contributed nothing, print `SKIPPED: <channel>: <reason>`. **At most one issue
   per run across all channels — the gate enforces it. Zero is acceptable.**

   End your run with a one-line-per-channel summary (the filed issue URL or
   `SKIPPED: <channel>: <reason>`) so the workflow step summary reflects the outcome.

## Rules

- **Read-only on this repo. No commits, no edits, no PRs.** The only mutations
  allowed are filing issues / comments via the guarded `cli.py file` / `comment`
  path (own tracker with the provenance label; in consumer mode also
  `dividedby/skills` with the cross-repo token). Direct `gh issue create` / `gh issue
  comment` are disallowed by the workflow's tool policy, so every filed body passes
  the leak guard by construction. The skill writes nothing to the tree.
- Read-only on `$MIRROR_DIR` and `$SKILLS_SRC`; never write back to either or to
  agent-research.
- Every filed body — **especially** any cross-repo one on the public tracker —
  passes the leak guard with the private markers (the shim runs it). Keep prose
  generalized regardless.
- `dividedby/skills` owns the `skill-request` and `skill-promotion` labels; a
  Consumer applies them, never creates them. Each repo owns its own `source:*`
  labels.
- At most one issue per run across all channels, gate-enforced; one is a
  ceiling, not a target. No questions. There is no user.
