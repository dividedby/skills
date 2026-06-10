# Stand up the roadmap-as-source-of-record pattern

This stands up a **human-readable roadmap as the execution source of record**:
one Markdown doc with a master census (one row per issue) that is the single
place you go to pick the next thing to work on, kept honest by two cheap hooks
and reconciled by the [`roadmap`](../../skills/engineering/roadmap/SKILL.md)
skill.

The three parts compose into a closed loop:

1. **`roadmap.md`** — the census; the only doc you read to choose work.
2. **A PreToolUse `git commit` guard** (`roadmap-guard.py`) — in-branch
   enforcement: an issue-referencing commit must touch the roadmap.
3. **A SessionStart drift nudge** (`roadmap-drift-nudge.py`) — catches
   *out-of-band* drift (issues opened/closed via `gh`/web *between* sessions,
   which the commit guard structurally can't see), and points at `/roadmap`.

`roadmap` is the reconcile half: the guard keeps the doc fresh *inside* a PR;
the nudge tells you when *between-PR* drift has accumulated; the skill fixes it.

### Roadmap vs. Idea Inbox: source of record vs. intake

These are two different surfaces, and onboarding wires both:

- The **Roadmap** (`roadmap.md`) is the **execution source of record** — the one
  doc you read to pick the next thing to work on. Every open issue lands here as
  a census row.
- The **Idea Inbox** (a single `idea-inbox`-labelled GitHub issue, one per repo —
  see `.github/ISSUE_TEMPLATE/idea-inbox.md`) is the **intake** for freeform,
  unstructured ideas. Items enter *enriched* (idea + ambient context/links) and
  leave by *draining* into tracked issues.

The invariant tying them together: **every filing registers in the Roadmap — not
every filing funnels through the Inbox**
([ADR 0021](../adr/0021-idea-inbox-is-the-unstructured-intake-everything-registers-in-the-roadmap.md)).
Structured, contract-bearing filings (skill-request, skill-promotion, a
fully-scoped bug) bypass the Inbox and file labeled issues directly; the drift
nudge still slots them into the census. Pick work from the Roadmap, not the
Inbox.

## The turn-key path

In a repo with issues but no roadmap, run **`/roadmap`**. It detects the empty
state and **bootstraps the whole pattern** — drops the roadmap template, backfills
one census row per open issue, writes both hooks into `.claude/hooks/`, wires
`settings.json`, and runs a first reconcile pass to populate statuses/waves/deps.
It writes everything to the working tree for review and **commits nothing**: you
review `git diff` + the new untracked files and commit.

If a legacy planning doc already exists (an older `ROADMAP.md`, a TODO/tracking
doc), `/roadmap` instead **migrates** it — proposing a mapping into the canonical
census before reshaping, preserving your prose.

### Migrate: a worked example

The two legacy shapes you'll meet most are a `## TODO` checklist (in a README or
a planning doc) and an exported GitHub **Projects** board. Migrate maps each
legacy entry to a census row and each legacy state to the closest canonical
`Status`. A checklist like:

```md
## TODO
- [x] #41 wire the auth middleware
- [ ] #42 rate-limit the login route   (blocked on #41)
- [ ] #43 add the audit-log table       — needs design
```

maps to the canonical census (and `/roadmap` *proposes* this mapping before
writing it):

| # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |
| - | ----- | ---- | ------ | ----- | -------- | ---- | ----- |
| 41 | wire the auth middleware | W1 | **Done** | agent | — | — | — |
| 42 | rate-limit the login route | W1 | **Next** | agent | `/tdd` | _#41_ | — |
| 43 | add the audit-log table | W1 | **Parked** | mixed | — | — | needs design |

Legacy → canonical `Status` mapping used above:

- `- [x]` (checked) → **Done** (and the issue is expected closed on GitHub).
- `- [ ]` with no blocker → **Next**/**Backlog** per the doc's ordering.
- `- [ ]` annotated "blocked on #N" → **Blocked**, with `#N` in `Deps`
  (_italic_ once that dep closes).
- `- [ ]` annotated "needs design"/"someday"/"wontfix" → **Parked**.

A Projects board migrates the same way: each card is a row, and the board's
columns (`Todo`/`In progress`/`Blocked`/`Done`) map to `Backlog`-or-`Next` /
`Next` / `Blocked` / `Done`. Freeform card notes carry into the `Notes` cell.

## What bootstrap creates, and why

Everything repo-specific is three things, hoisted to a config block at the top of
each hook so adoption is "edit a few constants":

- **`ROADMAP` path** — where the doc lives (`docs/plans/roadmap.md` default,
  `ROADMAP.md`, …). The hooks and the skill share this constant.
- **Census column indices** — `ISSUE_COL` / `STATUS_COL` (zero-based) tell the
  nudge's parser which pipe-delimited columns hold the issue number and the
  status. The template ships the default schema
  `| # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |`; the parser
  keys off index, so a repo with a differently-shaped table just sets the indices.
- **Status vocab** — `DONE_TOKEN`, the substring (lowercased) in a status cell
  that means closed/done.

The artifacts are pure Python stdlib
([ADR 0004](../adr/0004-runbook-helpers-are-python-stdlib.md)) and live as
**templates** under the skill
([`templates/`](../../skills/engineering/roadmap/templates/)) — they are not
active hooks in this repo; bootstrap copies them into a consumer.

### `settings.json` wiring

```jsonc
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [
        { "type": "command", "command": ".claude/hooks/roadmap-guard.py",
          "if": "Bash(git commit*)", "timeout": 15,
          "statusMessage": "Checking roadmap is updated..." }
      ]}
    ],
    "SessionStart": [
      { "hooks": [
        { "type": "command", "command": ".claude/hooks/roadmap-drift-nudge.py",
          "timeout": 15, "statusMessage": "Checking roadmap for out-of-band drift..." }
      ]}
    ]
  }
}
```

A project-scope hook may redeclare a global guard for CI/AFK parity
([ADR 0013](../adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md)).

### Footgun: branch-guard + a compound `checkout -b … && commit`

If the consumer repo *also* runs a **branch-guard** (a PreToolUse hook that
refuses commits on `main`), do **not** create the branch and commit in one
compound command. A `git checkout -b feature && <commit>` is read by the
PreToolUse hook *before* the command runs, so it sees the **current** branch
(still `main`) — the not-yet-executed `checkout -b` doesn't help, and the commit
is denied. **Create the branch in a separate step from the first commit:**

```sh
git checkout -b feature      # step 1: switch branches
# … stage your changes …
git commit -m "… #NN"        # step 2: now on `feature`, the branch guard passes
```

This pairing (a roadmap guard plus a branch guard) is a very common combo, so
it's a near-guaranteed stumble if you chain the two steps.

## Manual setup (if you'd rather not let the skill scaffold)

1. Copy [`templates/roadmap.md`](../../skills/engineering/roadmap/templates/roadmap.md)
   to your chosen path; backfill one row per open issue.
2. Copy the two hooks under `.claude/hooks/`, edit the config block (path / column
   indices / status vocab), `chmod +x`.
3. Wire `settings.json` (snippet above).
4. `npx skills@latest add dividedby/skills` → pick `roadmap`.
5. **Smoke-test both halves:**
   - *Nudge:* run the parser test
     (`python3 .claude/hooks/roadmap-drift-nudge.test.py`) to confirm your column
     config; run it by hand (`echo '{}' | .claude/hooks/roadmap-drift-nudge.py`)
     and confirm it reports your real drift.
   - *Guard:* run its test (`python3 .claude/hooks/roadmap-guard.test.py`), then
     confirm the enforcement half end-to-end with a deny case and an allow case
     (`<commit>` = your literal `git commit` invocation):

     ```sh
     # deny: issue-ref commit that doesn't touch the roadmap → exit 2
     printf '{"tool_input":{"command":"<commit> -m \\"fix #999\\""}}' | .claude/hooks/roadmap-guard.py; echo $?
     # allow: non-issue commit → exit 0
     printf '{"tool_input":{"command":"<commit> -m \\"chore: x\\""}}' | .claude/hooks/roadmap-guard.py; echo $?
     ```

     (The deny case only fires when the roadmap isn't already staged/changed in
     the branch — run it from a clean branch. And note this smoke command itself
     contains `git commit … #999`, so if the guard is *already* wired in your
     session it may gate the very call you use to test it — see the SKILL.md
     Gotchas.)
   - Finally, run `/roadmap` once to reconcile.

## Posture

`roadmap` edits the working tree for review and writes **additive** issue
comments (unblock/routing/sequencing notes); it **never commits, never closes an
issue, never rewrites a body** — see
[ADR 0017](../adr/0017-roadmap-write-posture.md). If you ever wire it into an
unattended loop, suppress the issue-write surface (propose-only), the same way the
staleness-review loop suppresses its apply station.
