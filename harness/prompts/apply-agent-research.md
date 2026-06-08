# Scheduled apply-agent-research pass

You are running unattended in GitHub Actions. No user is watching. Do not ask
questions — make the call yourself. Your job is to apply the `apply-agent-research`
skill to **this** repo and file **at most one issue per channel**, or none (see
the skill's `proposal-flow.md` and ADR 0011 in the skills repo).

This one prompt serves **both** the skills repo (the tracker **host**) and every
downstream **Consumer**; it reads its wiring from the environment the workflow stub
exports (see [ADR 0015](../adr/0015-apply-agent-research-prompt-is-consumer-portable-via-env.md)).
**Never hardcode a skill path** — invoke the installed skill at `$SKILL_DIR/SKILL.md`
and follow it. **Read both `$SKILL_DIR/SKILL.md` and `$SKILL_DIR/proposal-flow.md`
before acting** — this prompt is only the concrete wiring.

## Your role: host or consumer (derived from `$SKILLS_TRACKER_TOKEN`)

Branch your whole run on whether **`$SKILLS_TRACKER_TOKEN` is set**:

- **Unset → host mode.** You are running inside `dividedby/skills` itself. There is
  no cross-repo channel: you **drain** incoming `skill-request` issues on this
  tracker and propose skills on general merit, all into **this** repo with the
  default `GH_TOKEN`. Never write to another repo.
- **Set → consumer mode.** You are a downstream Consumer. You file/+1 the cross-repo
  `skill-request` (demand) and — only if this repo has local non-published skills —
  `skill-promotion` (supply) channels into `dividedby/skills`, authenticating those
  calls with `$SKILLS_TRACKER_TOKEN`.

The token is an honest discriminator: the host writes to itself with the default
`GITHUB_TOKEN` and never sets the cross-repo PAT, so its presence cannot drift out
of sync with the cross-repo writes it gates.

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
  `python3 $SKILL_DIR/lib/cli.py {gate,file,comment}`. Never a hardcoded path.
- **`$PRIVATE_MARKERS`** — space-separated private tokens for the leak guard. Expand
  to one repeatable `--marker <token>` per token on **every** guarded `file` /
  `comment` call (see Filing). Empty (the host case, and any fully-public repo) → no
  `--marker` flags, and the guard's structural checks still apply.
- **`$SKILLS_TRACKER_TOKEN`** — your role discriminator (above) and the cross-repo
  GitHub credential in consumer mode.
- **This repo's own governance docs:** `CONTEXT.md`, `CLAUDE.md`, every file under
  `docs/adr/`, and any skills under the repo. Use them as the ethos-fit oracle *and*
  the already-do-this filter. Treat ADRs as binding.

## Channels (run only the ones your role enables)

Each channel is capped **independently** — ≤1 issue per channel per run, zero fine.
A forced finding is worse than none.

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
   the motivating KB note.

3. **`skill-request` demand channel (consumer mode only)**
   (`$SKILLS_SRC/docs/design/skill-request-flow.md`) — when the KB mapping lands on a
   capability that *should* exist as a published skill but does not:
   - **Filter already-do-this FIRST** (ADR 0009): match the candidate against the
     published catalog (`$SKILLS_SRC/skills/...`, `plugin.json`) **and**
     `$SKILLS_SRC/docs/agents/installed-skills.md`. If either covers it, **do not
     file** — print `SKIPPED: skill-request: already covered by <name>`.
   - Otherwise list open requests:
     `GH_TOKEN="$SKILLS_TRACKER_TOKEN" gh issue list --repo dividedby/skills --label skill-request --state open`
     and match on the `<!-- capability: <slug> -->` marker. The slug names the
     *wanted capability*, so a different repo with the same gap produces the same slug.
     - **No match** → file a new issue in `dividedby/skills` via the guarded shim,
       following the full contract: capability wanted (generalized); the *specific,
       traceable* motivating KB note; why a published skill (broadly useful, and
       skill-shaped — not a run-book or harness feature); what it does **not**
       duplicate; the requesting repo (`$GH_REPO`); and the `<!-- capability:
       <kebab-slug> -->` marker. File as in step 5 with `--repo dividedby/skills
       --label skill-request` and the cross-repo token.
     - **Match** → do **not** open a second issue. `+1` via the shim's comment path
       (body = `+1 — also wanted by <this repo>` plus this repo's own motivating
       knowledge), with the same token, `--repo`, and markers.
   - All `dividedby/skills` calls MUST use `GH_TOKEN="$SKILLS_TRACKER_TOKEN" ...
     --repo dividedby/skills`. Never the default `GITHUB_TOKEN` (own-repo scoped →
     403). Read-only `gh issue list` may use a bare `gh`; create/comment go through
     the shim. **Apply** the existing `skill-request` label; **never** create it (the
     skills repo owns it).

4. **`skill-promotion` supply channel (consumer mode, local skills only)**
   (`$SKILLS_SRC/docs/design/skill-promotion-flow.md`) — for each **promotable**
   local skill from the supply-side audit (ADR 0010): list open
   `skill-promotion` issues in `dividedby/skills`, match on the `<!-- capability:
   <slug> -->` marker, and **file** (capability offered/generalized; why it clears
   general merit and is skill-shaped; a pointer to where the implementation lives —
   never a paste; not-already-covered; `$GH_REPO`; the marker) **or `+1`**, exactly
   like step 3 but with `--label skill-promotion`.

5. **Gate, per channel.** Run the one-proposal gate **once per channel** over only
   that channel's candidates + that channel's open keys, exactly as
   `proposal-flow.md` describes:
   `printf '%s' '<json>' | python3 "$SKILL_DIR/lib/cli.py" gate` (run from the repo
   root). The leak guard is **not** a standalone step — it is folded into the guarded
   filing path (step 6), which sanitizes `title + body` and files **only on ALLOW**.

6. **File or skip, per channel — via the guarded shim only.** Direct `gh issue
   create` / `gh issue comment` are disallowed by the workflow's tool policy; file
   through `cli.py file` / `cli.py comment`, which run the leak guard on `title +
   body` and act **only on ALLOW**. **Pass every private marker:** expand
   `$PRIVATE_MARKERS` (space-separated) to one `--marker <token>` per token on every
   `file` / `comment` call (none when it is empty). Write each body to a file (e.g. a
   heredoc into `$RUNNER_TEMP/body.md`) ending in the `dedup-key` marker + a short
   Sources line citing the knowledge note(s), then:
   - **self-improvement** (own tracker — host and consumer):

         python3 "$SKILL_DIR/lib/cli.py" file \
           --title "<title>" --body-file "$RUNNER_TEMP/body.md" \
           --label source:agent-research <expanded --marker flags>

   - **host-mode skills-on-general-merit / drained skill-request** → file into the
     own tracker the same way (own provenance label, own token).
   - **consumer-mode `skill-request` / `skill-promotion`** → cross-repo, with
     `GH_TOKEN="$SKILLS_TRACKER_TOKEN"`, `--repo dividedby/skills`, the channel's
     label, and the expanded `--marker` flags, as in steps 3–4.

   On `BLOCK: <reason>` it files nothing and exits non-zero — revise the body to drop
   the structural trigger (a fenced block, a pasted import, a `path/like.this` token,
   or a marker hit) and re-run; never route around it. For every channel that returns
   nothing, print `SKIPPED: <channel>: <reason>`. **At most one issue per channel.
   Zero is acceptable.**

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
- At most one issue per channel. No questions. There is no user.
