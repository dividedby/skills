---
name: roadmap
description: >
  Reconcile a repo's human-readable roadmap (a master census of every issue) with
  live GitHub issue state, so the doc stays trustworthy enough to be the only thing
  you read to pick the next task. Detects state and routes: bootstrap the whole
  pattern in a fresh repo, migrate a legacy planning doc into the canonical format,
  or reconcile an existing roadmap. Reconcile auto-applies its edits behind a green
  gate — branch → PR → auto-merge — and writes additive issue comments; it never
  direct-pushes to the default branch, never auto-closes an issue, and never rewrites
  a body. Use when a SessionStart drift nudge fires, on a cadence, when standing up
  the roadmap pattern, or any time the census looks stale against `gh`.
---

# Roadmap

A repo can make one Markdown roadmap its **execution source of record**: a master
census with one row per issue (status, wave, owner, skill routing, deps) that is
the single place you go to pick the next thing to work on. Two cheap hooks keep
it from rotting — a PreToolUse guard forces an issue-referencing commit to touch
the roadmap (in-branch freshness), and a SessionStart nudge reports *out-of-band*
drift (issues opened/closed via `gh`/web between sessions, which the commit guard
structurally cannot see). This skill is the **reconcile half**: it repairs the
drift the nudge reports, and stands the whole pattern up where it does not exist.

The guard enforces freshness **by the issue-reference convention** — a commit
must touch the roadmap only when its message carries a `#NN`. That makes it
convention-deep, **not a guarantee**: omitting `#NN` is *both* the documented
infra-commit escape *and* a silent bypass of the guard. The SessionStart
drift-nudge is the actual integrity net — it catches the drift the guard let
through. Wire and trust **both**; the guard alone is a nudge, not a lock.

Reconcile is an **applying loop, gated on green** ([ADR 0022](https://github.com/dividedby/skills/blob/main/docs/adr/0022-roadmap-reconcile-auto-applies-on-a-green-gate.md),
amending [ADR 0017](https://github.com/dividedby/skills/blob/main/docs/adr/0017-doc-regen-write-posture.md)): the
reconcile edit is a mechanical census projection of live `gh` state, so it lands
its own changes — **branch → commit → PR → auto-merge** — rather than prompting a
human to review-and-commit. The repo's **green gate** (hook self-tests,
`check-skill-registration`, any CI) is the safety, not a human click; the PR is the
audit trail. It **never direct-pushes to the default branch**. Two invariants from
ADR 0017 still hold: issue writes stay **additive** (comments, never a body
rewrite), and **closing stays a human act** — even Tier-3's agent-powered doneness
verdict only recommends. This posture is identical in interactive and loop runs;
the green gate, not a watching human, is the control. The *proposal-loop* family
(apply-agent-research, arch-review) is untouched and stays propose-only
([ADR 0003](https://github.com/dividedby/skills/blob/main/docs/adr/0003-skill-improvement-workflows-propose-via-issues.md)) —
reconcile is deterministic maintenance of the maintainer's own roadmap, a
categorically different thing from auto-applying a judgment proposal.

The bootstrap and migrate modes, which edit human-authored artifacts, still
**checkpoint their judgment for review** before writing (see those sections).

## The body is human-facing; the protocol lives here

Per [ADR 0024](https://github.com/dividedby/skills/blob/main/docs/adr/0024-inbox-roadmap-bodies-are-human-facing-instructions-live-in-skill-docs.md),
the roadmap **body is the human-facing surface** — a read-only-mirror banner, a
one-line `## Burn-down`, the `## Census`, and a single consolidated `## Legend`,
nothing more. The agent **operating instructions live here, in this skill**, not
in the body: there is no `How to use this doc` and no `Self-update protocol`
section to load every time an agent acts. Status/Owner/Skill/Wave vocabulary is
stated **once**, in the Legend. The closed-wave lifecycle and the self-update
contract (an issue-referencing PR updates that issue's row in the same branch) are
documented in this skill (Reconcile tiers + Boundaries) — not duplicated into the
body.

The body carries exactly one machine-readable affordance: a hidden
**breadcrumb** HTML comment as the **first line** of the doc, the backstop
discovery path for an agent that reads the raw body without entering via the
skill. The schema is owned here (ADR 0024 defers it to this file):

```
<!-- agent-protocol: reconcile=/roadmap; drain=docs/agents/idea-inbox.md -->
```

- It is **invisible** in the rendered GitHub/mirror view (an HTML comment), so it
  costs the human nothing while giving a raw-body reader an explicit path.
- `reconcile=/roadmap` names this skill's invocation directly — an agent reading the
  raw body resolves it to this skill; `drain=docs/agents/idea-inbox.md` points at the
  inbox-drain doc.
- It is **two fields, `;`-separated**, the same shape in the Roadmap and the Idea
  Inbox bodies. Keep it as the first line so a raw reader hits it before anything else.

The mirror is **unchanged** by this layout. `roadmap-mirror.render()` stays a
faithful render of the working-tree doc (ADR 0020) — the breadcrumb renders to
nothing, the thinner body renders verbatim; render behavior is not touched.

## The front door — detect state, then route

The first thing every run does is decide *which mode* it is in. **Resolve the
roadmap path before routing — never assume the default**, because a census may
already live at a non-default path, and concluding bootstrap against a hardcoded
default silently writes a *second*, duplicate census (the skill's one
correctness sin — see Anti-Patterns):

0. **Discover the path first.** Do not trust the `docs/plans/roadmap.md` default
   blindly. (a) If a hook is already installed
   (`.claude/hooks/roadmap-guard.py` / `roadmap-drift-nudge.py`), read the
   `ROADMAP` value from its config block — that is the authoritative path for
   this repo. (b) If no census sits at that path, **glob for an existing census**
   anywhere in the repo (`**/*.md` plus the repo root) and detect it by its
   **census signature**: a markdown table whose header carries *both* an
   issue-number column (`#`/`Issue`) and a `Status` column. Only after this
   discovery comes up empty may you conclude bootstrap.

Then route:

1. **Canonical roadmap present at the configured path** (it exists and parses as
   a census) → **reconcile** — *unless* its body is still in the **legacy layout**
   (prose-heavy census cells over the ~120-char cap, embedded `How to use this
   doc` / `Self-update protocol` operating-instruction sections, an unbounded
   inbox `Actioned` list with no rolling window). A census can parse as canonical
   yet predate the thin layout (ADRs 0024/0025); that pair routes to **migrate the
   intake pair** (below), a one-time human-reviewed thinning, before normal
   reconcile resumes. The legacy-layout tell is structural, not about issue state:
   look for the removed instruction sections, over-cap cells, or a missing
   breadcrumb. The common case is the already-thin body → reconcile, just keeping
   it honest.
2. **A census exists at a non-default path** (found by the signature glob above)
   → **relocate, never duplicate**. `git mv` it to the canonical default
   `docs/plans/roadmap.md`, update every reference (hook config blocks,
   `settings.json` hook paths, any in-repo links), then **reconcile in place**.
   The decision is *relocate to canonical*, not adopt-in-place — one path, one
   census. Do not write a fresh roadmap alongside the one you found.
3. **No census anywhere, but a legacy planning doc exists** (an older `ROADMAP.md`,
   a `docs/plan*`, a TODO/tracking doc, a project board exported to markdown that
   does *not* match the census signature) → **migrate**. Adapt the existing
   artifact into the canonical format.
4. **Nothing — no census signature anywhere, no legacy doc** → **bootstrap**.
   Stand the whole pattern up from scratch.

Distinguishing (3) from (4) is a judgment call — look for any human-maintained
list of work before concluding there is nothing to adapt. When unsure, treat it
as migrate and *propose* the mapping rather than overwriting silently. The
census-signature glob in step 0 is what keeps an already-canonical-but-misplaced
doc from ever falling through to (4).

## Bootstrap — stand the pattern up (turn-key)

Run in a repo that has issues but no roadmap. Scaffold everything to the working
tree for review (never committed):

- **Checkpoint the judgment before writing.** Assigning waves / statuses / deps
  is the same tier-2 judgment the Reconcile section says to *propose first, then
  write* — and the hook wiring you are about to add will constrain every future
  issue-referencing commit in the repo. So before scaffolding, **state the
  proposed wave/census mapping and the hook wiring for review**, then write. The
  rest of bootstrap is one pass to the working tree; only this judgment layer is
  checkpointed first, so the operator reviews the mapping deliberately rather
  than improvising a confirmation after the diff already exists.
- **Drop the roadmap.** Copy [`templates/roadmap.md`](templates/roadmap.md) to
  `ROADMAP`, fill the project name, and **backfill one census row per open
  issue** from `gh issue list` — then run the reconcile tiers below to set
  statuses, waves, and deps so the doc lands populated, not empty. The
  `## Burn-down` section drops pre-populated: it is recomputed from that first
  census backfill the same way reconcile recomputes it every pass (Tier-1
  mechanical).
- **Wire the two hooks.** Copy [`templates/roadmap-guard.py`](templates/roadmap-guard.py)
  (PreToolUse) and [`templates/roadmap-drift-nudge.py`](templates/roadmap-drift-nudge.py)
  (SessionStart) into `.claude/hooks/`, `chmod +x`, and **edit each file's config
  block** to the repo's roadmap path. The nudge auto-derives its census columns
  from the table header, so most repos need no column edits — set `ISSUE_COL` /
  `STATUS_COL` only to override, and `DONE_TOKEN` (emoji-aware, e.g. `✅`) to the
  repo's done marker. In `roadmap-guard.py`, set `BASE_BRANCH` to the branch(es)
  the PR merges into — a **list** for two-hop repos (feature→staging→main), so
  the roadmap counts as touched if it changed vs any base.
- **Ship both `.test.py` files and run them** beside the hooks
  ([`roadmap-drift-nudge.test.py`](templates/roadmap-drift-nudge.test.py) confirms
  the parser config matches your table;
  [`roadmap-guard.test.py`](templates/roadmap-guard.test.py) pins the commit
  guard). Run with `python3 -B` (bytecode disabled) and add `__pycache__/` to
  `.gitignore` as a bootstrap step — both prevent the self-test from leaking a
  `__pycache__/` dir into the tracked `.claude/hooks/` diff the human is about to
  review and commit.
- **Register the hooks in `settings.json`** — a `PreToolUse` matcher on `Bash`
  for the guard and a `SessionStart` entry for the nudge. **Merge into the
  existing arrays; never clobber.** `hooks.PreToolUse` and `hooks.SessionStart`
  are very likely already populated, so *append* these entries to whatever is
  there rather than overwriting the keys. The canonical shape (illustrative —
  paths/matcher follow the repo's conventions, ADR 0002):

  ```jsonc
  {
    "hooks": {
      "PreToolUse": [
        // ── append this; keep every existing PreToolUse entry ──
        {
          "matcher": "Bash",                       // guard only inspects Bash git commits
          "hooks": [
            { "type": "command", "command": "python3 -B .claude/hooks/roadmap-guard.py" }
          ]
        }
      ],
      "SessionStart": [
        // ── append this; keep every existing SessionStart entry ──
        {
          "hooks": [                                // no matcher: SessionStart entries don't take one
            { "type": "command", "command": "python3 -B .claude/hooks/roadmap-drift-nudge.py" }
          ]
        }
      ]
    }
  }
  ```

  - **Matcher presence/absence.** The `PreToolUse` guard **needs** a matcher
    (`"Bash"`) so it only fires on shell commands; the `SessionStart` nudge takes
    **no** matcher — omit the key, don't set it to `""`.
  - **If a matching `Bash` PreToolUse entry already exists**, add the guard
    command to that entry's `hooks` array rather than adding a second `"Bash"`
    matcher block.
  - **Redeclaring a global guard is allowed for CI/AFK parity.** Hooks are
    additive across scopes, but a project-scope hook **may** redeclare a global
    guard when the run lacks `~/.claude/` (the AFK/CI `claude -p` case), because
    the project copy is then the *only* one that runs
    ([ADR 0013](https://github.com/dividedby/skills/blob/main/docs/adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md)).
  - **Verify before handing off:** validate the JSON (`python3 -m json.tool
    .claude/settings.json`), run the parser self-test
    (`python3 -B .claude/hooks/roadmap-drift-nudge.test.py`), and run the nudge
    once against the real roadmap to confirm it parses the live table.

- **Stand up the Idea Inbox and register it as a Meta census row (ADR 0021).**
  The roadmap pattern and the Idea Inbox are one intake system — the census is
  the *execution* source of record, the Inbox is the canonical intake for
  *unstructured* human-originated ideas — so a fresh-repo bootstrap stands both
  up together. Scaffold the single per-repo Inbox issue carrying the reworked
  **enriched-intake + self-prescribing-drain** content from
  [`.github/ISSUE_TEMPLATE/idea-inbox.md`](../../../.github/ISSUE_TEMPLATE/idea-inbox.md)
  (intake captures the idea *plus* its ambient context; drain is self-prescribed
  in the issue body, picking only the pipeline steps each idea needs — no
  separate skill), and **add it as one Meta-bucket row** in the master census
  (the Legend's Meta bucket — `idea-inbox` / onboarding — already names it, so
  this is a single row, not a new column or section). It's a `Tracking`-shaped,
  human-owned standing row, not loop work. **No new reconcile sync code is
  needed:** the Inbox is just one more open issue in the census, and the
  existing SessionStart drift nudge already flags both **drained** issues (the
  ones the Inbox spins out) and **directly-filed** issues (structured filings
  that bypass the Inbox per ADR 0021), so reconcile slots them through the
  ordinary tier-2 path — bootstrap only adds the Inbox to what it creates.
- **Install the read-only mirror (ADR 0020), optional but recommended.** Copy
  [`templates/roadmap-mirror.py`](templates/roadmap-mirror.py) to
  `.github/scripts/` and [`templates/roadmap-mirror.yml`](templates/roadmap-mirror.yml)
  to `.github/workflows/`, then edit the `paths:` filter, `MIRROR_ISSUE`, and
  `ROADMAP_PATH` to the repo's roadmap doc and the pinned mirror issue. Title
  the pinned issue **`🗺️ Roadmap`** — the map emoji plus `Roadmap`, nothing
  more. **"Read-only" never goes in the title**; the read-only status is carried
  by the body banner that `render()` prepends, so it lives in the issue body, not
  the heading. The
  workflow renders the doc into a machine-owned mirror issue body on every push
  that touches it, **commit-if-changed**. The render
  (`render()`) is pure and the only I/O is the injected `gh` seam, so its
  self-test ([`roadmap-mirror.test.py`](templates/roadmap-mirror.test.py))
  never makes a live call — ship and run it beside the script with `python3 -B`.
  **The skill never writes the mirror; CI owns it** — the mirror body is a
  machine-owned render target, not a human-authored body, so it sits outside the
  skill's write-posture rules (ADR 0017 carve-out, ADR 0020).

Bootstrap writes files but **commits nothing** — finish by telling the human to
review `git diff` and the new untracked files, then commit.

## Migrate (legacy doc) — adapt a legacy planning artifact into the canonical format

Run when an older planning artifact exists that does *not* match the census
signature (an `ROADMAP.md`, a `docs/plan*`, a TODO/tracking doc). The goal is to
*preserve* the human's content while reshaping it onto the census:

- Read the legacy doc and map its entries onto canonical rows (issue #, status,
  wave, owner, skill, deps), inferring the closest canonical `Status` for each
  legacy state. **Preserve prose** — carry freeform legacy notes into the `Notes`
  cell or a section above the census; do not discard human context.
- **Propose the mapping before reshaping.** Migration edits a human-authored
  artifact, so state the proposed census (and any ambiguous legacy→canonical
  status mappings) for review *first*, then write it.
- Once the canonical roadmap exists, fall through to reconcile to fill gaps
  against live issue state, and wire the hooks as in bootstrap.
- This route produces a thin canonical body straight away, so it does **not** also
  need the intake-pair thinning below. (The route below is for a pair that is
  *already* canonical-as-a-census but predates the thin **layout**.)

## Migrate (intake pair) — thin a legacy-layout Roadmap + Inbox in one human-reviewed PR

Run when the repo's intake pair already parses as canonical (a census table, a
per-repo `idea-inbox` issue) but its **layout predates the thin format** of ADRs
[0024](https://github.com/dividedby/skills/blob/main/docs/adr/0024-inbox-roadmap-bodies-are-human-facing-instructions-live-in-skill-docs.md)
/ [0025](https://github.com/dividedby/skills/blob/main/docs/adr/0025-census-cells-are-thin-pointers.md):
prose-heavy census cells over the ~120-char cap, embedded `How to use this doc` /
`Self-update protocol` operating-instruction blocks, an unbounded inbox `Actioned`
list, or a missing breadcrumb. This is a **one-time** reshape that brings both
artifacts of the [ADR 0021](https://github.com/dividedby/skills/blob/main/docs/adr/0021-idea-inbox-is-the-unstructured-intake-everything-registers-in-the-roadmap.md)
intake pair onto the new layout. **It is the only route that touches the inbox** —
ongoing reconcile never does (see Boundaries).

This route is **distinct from reconcile and bootstrap**: reconcile keeps an
already-thin census honest and auto-merges; bootstrap stands the pattern up in a
fresh repo; this thins an existing legacy-layout pair and is **human-reviewed, not
auto-merged**.

### Non-lossy first — relocate orphan narrative before any trim

The thinning is **lossy** (it deletes prose), so context preservation comes
*before* deletion, never after:

- For every census **cell** about to be trimmed and every **Actioned** item about
  to be pruned, check whether its narrative is **already on the linked issue `#N`**
  (body or a comment). If it is, the trim drops nothing — proceed.
- If the narrative is **orphan** (not already on the issue), **post it as an
  additive comment on `#N` first**, then trim. Relocation precedes the trim; it
  never follows it (ADRs 0025 §3, 0022 amendment). A cell or item with **no linked
  issue** cannot be relocated — surface it for the human rather than dropping it.
- This is the judgment a green gate cannot make — whether the relocated comment
  *faithfully* captures the trimmed prose — which is exactly why this PR is
  human-reviewed (below).

### Restructure the roadmap body

Reshape the roadmap to the thin layout that [`templates/roadmap.md`](templates/roadmap.md)
now seeds (the canonical target #228 established):

- **Strip the embedded operating instructions** — delete the `How to use this
  doc` and `Self-update protocol` sections from the body. The protocol lives here
  in this skill now; the body keeps only the read-only-mirror banner, the one-line
  `## Burn-down`, the `## Census`, and a single consolidated `## Legend` (ADR 0024).
- **Add the breadcrumb** as the **first line** if absent:
  `<!-- agent-protocol: reconcile=/roadmap; drain=docs/agents/idea-inbox.md -->`.
- **Backfill over-cap cells to thin pointers** — after relocating orphan narrative
  (above), trim each Notes/Status cell to a single ≤120-char line and Status to a
  single Legend token (ADR 0025). The deep context now lives on the relocated issue.
- **Recompute the `## Burn-down`** from the reshaped census Status column and stamp
  its date, exactly as Tier-1 reconcile does — so `roadmap-guard`'s
  Burn-down/census consistency check passes in-branch (#227).

### Restructure the sibling inbox in the same PR

Per ADR 0021 the inbox and roadmap are the coupled intake pair, so one migrate run
reshapes both:

- **Extract the drain protocol** to `docs/agents/idea-inbox.md` if it isn't already
  there (the canonical single source #229 established), and **strip the embedded
  `🤖 operating instructions` block** from the inbox body.
- **Add the breadcrumb** as the inbox body's first line if absent (same schema).
- **Prune `Actioned` to the rolling window** (~8 most recent; ADR 0024 / the drain
  doc) — but only **after** relocating any orphan Actioned narrative to its linked
  issue per the non-lossy step above. Older items drop off; their record survives
  on the `→ #N` they link.
- Leave the live `## Ideas` list intact — the thinning is about instructions and
  the Actioned window, not the un-actioned ideas.

### Land it — one human-reviewed PR, exempt from auto-merge

Both artifacts ship in a **single PR** ([ADR 0022 amendment](https://github.com/dividedby/skills/blob/main/docs/adr/0022-roadmap-reconcile-auto-applies-on-a-green-gate.md)):
branch off the default branch → commit the reshaped roadmap **and** inbox (plus the
extracted drain doc) → open a PR → **do NOT enable auto-merge**. A human approves
and merges. The green gate (hook self-tests, `check-skill-registration`, any CI)
still runs — it verifies *structure*: bodies parse, cells are under cap, Burn-down
is consistent — but it **cannot verify context preservation** across the lossy
trim, which is the whole reason a human reviews. This is the **one carve-out** from
ADR 0022's auto-merge posture; it is a one-time event and changes nothing in the
reconcile path, which keeps auto-merging behind the green gate. The PR body should
call out that it is a human-reviewed migration exempt from auto-merge, and list the
issues that received relocated narrative comments so the reviewer can spot-check
fidelity.

The migrate-intake-pair route reshapes the **layout**; it does not re-route, re-wave,
or re-scope rows (that is reconcile/Tier-2 judgment). After it merges, the next
ordinary `/roadmap` run reconciles the now-thin pair as usual.

## Reconcile — repair drift in three tiers

The core loop. Gather state once, then work three tiers of increasing judgment
and decreasing write-authority.

### Gather state
One `gh issue list --state open --json number,state,labels,title`; read and parse
the census (the parser keys off column *index*, per the hook's config — do not
re-derive it from a hardcoded schema); `git log` / `git diff` / grep the working
tree for the tier-3 cross-check. One network call to `gh`; no product or live data.

**Derive closed-state — never bulk-load it.** The open set plus the census is
enough; closed-ness falls out by set-difference (issue #239), so the closed archive
is never queried:
- `unfiled_open` = an open number with **no** census row → tier-2 candidate.
- `stale_closed` = a census row **not** marked `Done` whose number is **absent**
  from the open set → it was closed; tier-1 flips it to `Done`.
- A census row whose number **is** in the open set → still open; run its label/title
  drift checks for routing.

"Absent from the open set" means closed *or* transferred *or* deleted; treating
absent-as-closed is correct for the flip-to-`Done` repair. If certainty is wanted
before an auto-flip, confirm only the absent numbers with a targeted
`gh api repos/{owner}/{repo}/issues/{n}` (REST, bounded by census size) — optional,
not required (issue #239). The drift-nudge hook (`roadmap-drift-nudge.py`) uses this
**same** derivation, so hook and skill stay in parity.

### Tier 1 — mechanical (write to the working tree)
Deterministic repairs that need no judgment, applied directly:
- A closed issue whose row is not `Done` → set `Status: Done`.
- **Closed-wave lifecycle ([ADR 0023](https://github.com/dividedby/skills/blob/main/docs/adr/0023-closed-waves-collapse-then-prune-census-is-an-execution-view.md)).** The census is an *execution view*, not the
  archive — keep the active backlog readable by collapsing then pruning closed work
  at **wave granularity**:
  - When *every* issue in a wave is `Done`, **collapse** that wave's rows into a
    `<details><summary>Closed wave W# — theme</summary>`. Open waves and the active
    census stay inline.
  - Once a *newer* wave is active, **prune** the collapsed wave's rows to a one-line
    wave summary and **bump the Burn-down cumulative closed-count integer** — bumped,
    never recomputed (pruned rows are gone). The rows are not lost: GitHub retains
    closed issues and git history retains every old row.
- A row whose blocking `Deps` have all closed → *italicize* the satisfied deps and
  flip `Blocked` → `Backlog`/`Next` per the doc's own ordering rules.
- Recompute wave and `Next` markers per the roadmap's stated ordering.
- **Recompute the `## Burn-down`** from the **census `Status` column in the
  working-tree doc** (never hand-bumped) and stamp its date. It is fully derivable
  from the reconciled census plus the one `gh` call already made — the `open` count
  is the number of census rows whose `Status` is not `Done`, and total / closed
  (pct), the five status-bucket counts and their issue lists, and the open-by-wave
  line are all projections of the table onto the `Owner` + `Status` + label
  vocabulary (see the roadmap Legend). So it carries no judgment: reconcile rewrites
  it wholesale every pass rather than diffing it. `roadmap-guard` enforces this
  consistency in-branch — it denies a commit whose Burn-down `open` count disagrees
  with the census Status column (issue #227). The one **carried-forward** field is
  the **cumulative closed-count integer** — it is *bumped* by the prune, not recomputed
  from the table (pruned rows are gone), so it survives wave pruning (ADR 0023).

### Tier 2 — semantic (propose the row, then write)
Newly-opened issues with no census row: slot each in with an **inferred** wave,
cluster, owner, skill routing, and deps. Because these are judgment calls, **state
the proposed row and the reasoning first**, then write it. Do **not** flag a child
that is already aggregate-covered by an epic/PRD parent row as "unfiled". The
nudge can't see aggregate coverage from the table alone, so when you create an
aggregate row, **add its child issue numbers to the nudge's `AGGREGATE_COVERED`
config set** (in `roadmap-drift-nudge.py`) — otherwise the nudge cries "unfiled"
on those children every session and trains the operator to ignore it. The list is
explicit and auditable by design; a future enhancement may parse `#NN–#NN`
enumerations out of aggregate rows, but that magic isn't built (it can mask
genuinely-unfiled issues).

### Tier 3 — active doneness investigation (recommend, never close)
For each open row, run a real investigation into whether the work is *done* —
don't settle for a passive "this file looks merged" glance. Inspect the **linked
PRs** (merged? CI green? scope matched?), read the **code and tests** the issue
asked for, and check the **plans** (the issue body, its acceptance criteria, any
referenced ADR). Synthesize that evidence into a **confident, well-grounded
recommendation**: done / not-done / partially-done, with the specific evidence that
backs it, so the human's close decision is a fast yes rather than a fresh
re-investigation. This tier may add an **additive comment** recording the verdict
(it shares the additive-only issue-write posture below), but it **never closes the
issue and never rewrites a body** — closing on inference is the one irreversible act
kept behind a human, by construction.

### Issue writes — additive only
As reconcile repairs the roadmap, keep the *issues* honest too, since the roadmap
points the working agent at them for authoritative scope (and the work-the-roadmap
protocol reads the full issue **including comments**). The write surface is
strictly additive ([ADR 0017](https://github.com/dividedby/skills/blob/main/docs/adr/0017-doc-regen-write-posture.md)):
- **Add/update a comment** when a dep closes and unblocks an issue, when routing
  or sequencing changes, or to record a tier-2 slotting decision — so the next
  agent reads it on the issue, not just in the roadmap.
- **Record blocker/dep changes** as comments and in the roadmap's `Deps` cell.
- **Never close an issue, never rewrite a body.** Closing stays a human act on a
  tier-3 recommendation; bodies are human-authored.

### Finish — land it behind the green gate
Reconcile **applies its own changes**: branch off the default branch, commit the
roadmap edits (and any Tier-2 additive slotting), open a **PR**, and **enable
auto-merge** so the repo's green gate (hook self-tests, `check-skill-registration`,
any CI) merges it once checks pass — no human prompt, no direct push to the default
branch. The PR body is the audit trail: summarize the three tiers (what Tier-1/2
auto-applied, what additive comments landed, and Tier-3's doneness verdicts with the
issues a human should review-and-close). This is the posture in **both interactive
and loop runs** — the green gate is the control, so a watching human is not required.
**Never direct-push to the default branch, never auto-close an issue.** If the gate
is red, the PR simply doesn't merge — that is the safety working, not a failure to
report around.

## Surfacing AFK-able work

Reconcile keeps the census honest, but the highest-leverage move before
dispatching an autonomous loop is **forward motion**: converting
`needs-triage`/`Parked`/`ready-for-human` issues into `ready-for-agent` ones,
often by carving an agent-doable slice out of something that looks blocked or
human-only. That call stays the maintainer's; this skill only *surfaces* it.

### The AFK-ability pass (report-only)
A separate report-only pass — it **never edits the roadmap and never touches
issues**, leaving the label/split call to the maintainer (the same human-decision
boundary Tier-3 keeps for closing). For each open `needs-triage`/`Parked`/
`ready-for-human` row, ask "is there a deterministic, judgment-free slice here?"
and flag the candidates for the maintainer, each with a one-line **what would flip
it** (the single decision or split that would make it `ready-for-agent`). This is
a recommendation surface, not a write: the human makes the label/split call
(ADR 0003/0017).

### The strong agent brief (the bar to be safely looped)
A flagged candidate is only worth looping once its issue clears this bar:
- **Clear module + acceptance criteria + TDD notes** — the existing
  `ready-for-agent` bar.
- **A determinism / offline boundary.** Inject the clock/rng rather than reading
  it; **stub external deps** (LLM/network/egress) behind an interface so the
  *suite* never makes a live call. The live run is a separate child.
- **A report-only boundary where applicable.** The agent measures/builds and
  **stops**; the maintainer owns any speculative follow-up — so an unattended loop
  never spawns judgment work.
- **Explicit out-of-scope + a single named follow-up owner.**

### Repeatable split patterns
Named carves that turn a blocked/human-only row into an AFK-able slice plus a
human sibling:
- **Mechanism vs HITL-copy split** — plumbing/logic → `ready-for-agent`;
  wording/taste → a `ready-for-human` sibling (e.g. build a prompt UI component
  with placeholder copy now, revoice it later).
- **Build vs live-run split** — TDD the machinery behind a stub now
  (`ready-for-agent`); the live backfill/cron/egress run is a `ready-for-human`/ops
  child.
- **Re-measurement carve-out** — when the levers a `Tracking` issue asked for have
  all shipped, the residual is often a deterministic *re-measurement* harness (a
  pure analyzer + a thin runner) — pure agent work.

The strong-agent-brief rubric is referenced from the roadmap template's Legend, so
a maintainer scaffolding a new repo inherits the bar.

## Boundaries

- **Static.** `gh` + working tree only — no product or live data, no network
  beyond the `gh` calls (`issue list`, comment, PR create/auto-merge).
- **Reconcile auto-applies behind a green gate; never direct-pushes.** It branches,
  commits, opens a PR, and enables auto-merge — the green gate merges it. The
  default branch is never written directly ([ADR 0022](https://github.com/dividedby/skills/blob/main/docs/adr/0022-roadmap-reconcile-auto-applies-on-a-green-gate.md)).
  (Bootstrap and the legacy-doc migrate, which touch human-authored artifacts, still
  scaffold to the working tree for review — see those sections.)
- **Reconcile never touches the inbox; only the intake-pair migrate does.** Ongoing
  reconcile is a census projection of the roadmap alone — it never edits the Idea
  Inbox issue. The **one** route that reshapes the inbox is the one-time
  intake-pair migrate (above), which thins Roadmap + Inbox together because ADR 0021
  makes them the coupled pair. That migrate run is **human-reviewed and exempt from
  auto-merge** — the single carve-out from ADR 0022's auto-merge posture (ADR 0022
  amendment), because relocating trimmed narrative faithfully is a judgment the green
  gate cannot make.
- **Additive on issues; closing stays human.** Comments and dep notes only — no
  close, no body rewrite. Tier-3 is an *active doneness investigation* that may add
  a verdict comment but never closes; the AFK-ability pass is report-only and never
  writes. The agent recommends; the human owns the irreversible close.
- **Same posture in interactive and loop runs — no loop-suppression for reconcile.**
  ADR 0022 **reverses** ADR 0017's loop-suppression invariant for the reconcile
  path: because the green gate (not a watching human) is the control, an unattended
  loop applies exactly as an interactive run does — it is an *applying loop* the
  `autonomous-loop` skill already blesses (commit/PR/merge on a green gate), not a
  proposal loop. The invariants that **do** survive into the loop are no-auto-close
  and no-body-rewrite. The *proposal-loop* family (apply-agent-research, arch-review)
  stays propose-only and envelope-suppressed
  ([ADR 0003](https://github.com/dividedby/skills/blob/main/docs/adr/0003-skill-improvement-workflows-propose-via-issues.md)) —
  reconcile is not in that family.
- **Complements, does not replace, `roadmap-guard.py`.** The guard keeps the doc
  fresh *inside* a PR; this skill repairs *between-PR* drift.

## Gotchas

- **The guard matches command *text*, not intent.** `roadmap-guard.py` enforces
  when the command string contains `git commit` *and* any `#NN` — it reads the
  literal command, so it cannot tell "I am committing" from "my command merely
  mentions a commit." A Bash call that *quotes* a commit (an `echo`/heredoc, a
  test harness, a `--dry-run`, a script, or a commit message that embeds another
  command string) can trip the guard even though nothing is being committed. If a
  legitimate non-commit command is denied, restructure it so the literal
  `git commit … #NN` text isn't present, or run it where the guard isn't wired.
- **The guard you just wired gates *your own* next commits this session.** Once
  bootstrap installs it, the very next issue-referencing commit in the session —
  including the bootstrap commit itself — must touch the roadmap or omit the
  `#NN`. This is correct behavior, but surprising: the operator wiring the guard
  is its first subject. (Smoke-testing the guard is itself an example of the
  text-match gotcha above — the smoke command contains `git commit … #NN`.)

## Anti-Patterns

- **Bulk-loading closed issue state (`gh issue list --state all`).** Closed state
  never needs to be queried — reconcile already enumerates every *open* issue, and
  closed-ness falls out by set-difference against the census (a non-`Done` census row
  whose number is absent from the open set was closed). Pulling `--state all` drags
  in the whole closed archive, unbounded by repo history, for nothing. Fetch
  `--state open` and derive the rest (issue #239); keep the drift-nudge hook in parity.
- **Deleting a closed row ad hoc — or keeping every closed row forever.** Both are
  wrong now ([ADR 0023](https://github.com/dividedby/skills/blob/main/docs/adr/0023-closed-waves-collapse-then-prune-census-is-an-execution-view.md) supersedes the old never-delete rule). The census is an
  *execution view*: a wholly-closed wave **collapses** into a `<details>` and its
  rows **prune** to a one-line summary once a *newer* wave is active, with the
  Burn-down cumulative count bumped. The wrong moves are pruning a row **before** its
  wave is collapsed-and-superseded, pruning **without** bumping the cumulative count,
  or collapsing an **open** wave. GitHub + git history are the archive — the census
  carries the active backlog, not the full ledger.
- **Flagging an aggregate-covered child as unfiled.** A child tracked by an
  epic/PRD parent row is represented; only genuinely unrepresented open issues
  are tier-2 candidates.
- **Auto-closing an issue, or editing its body.** Closing is a human act on a
  tier-3 recommendation; issue writes are additive comments only.
- **Direct-pushing the reconcile to the default branch.** Reconcile branches, opens
  a PR, and enables auto-merge so the green gate lands it — the default branch is
  never written directly, and there is no human review-and-commit step to wait on
  (ADR 0022).
- **Re-deriving the census schema from a hardcoded shape.** Parse by the hook's
  configured column index so the skill adapts to the repo's table.
- **Writing a duplicate roadmap.** Never conclude bootstrap against the hardcoded
  default path without first running the census-signature discovery (front-door
  step 0). A census found at a non-default path is *relocated* to canonical, never
  duplicated.
- **Restating issue scope in the roadmap.** The census routes and orders; the
  issue body (plus comments) is authoritative for scope (ADR 0002 — principle,
  not a fixed column layout).
