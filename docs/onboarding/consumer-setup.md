# Onboard a repo as an `apply-agent-research` Consumer

This is the durable procedure for wiring a repo up as a **[Consumer](../../CONTEXT.md)**
in the decentralized-pull knowledge-application system: it (a) improves its own
agent-meta from the shared knowledge base and (b) participates in the cross-repo
`skill-request` (demand) and `skill-promotion` (supply) channels.

**One loop, two concerns, two owners — you onboard it once.** Concern (a) is
`agent-research`'s domain: the knowledge it synthesizes and mirrors. Concern (b)
is this repo's domain: it owns the `skill-request` / `skill-promotion` labels and
their contracts (`docs/design/skill-request-flow.md`,
`docs/design/skill-promotion-flow.md`). They are **not** two separate loops — the
demand/supply channels are emitted *by* the single `apply-agent-research` run, off
the same KB read, so there is exactly one thing to set up. This doc lives here, in
the **public** skills repo, on purpose: a Consumer clones a credential-free read
surface (the knowledge mirror) and frequently has no access to the private
`agent-research`, so its onboarding must be readable without that access. Ownership
of concern (a) is expressed **by reference** to `agent-research`, not by relocating
this procedure behind its wall.

`apply-agent-research` is the **rich** member of the
[proposal-loop family](./proposal-loop-harness.md) — **read that harness doc
first**; this doc adds only what is Consumer-specific. Hand this file (plus the
parameters below) to an agent running inside the target repo. The agent
**proposes the setup, implements it on a branch, and opens a PR** — it never
pushes to the default branch.

## Parameters (fill in for the target repo)

| Parameter | Meaning |
|---|---|
| `CONSUMER_REPO` | `owner/name` of the repo being onboarded |
| `IS_KNOWLEDGE_SOURCE` | `yes` only if this repo **is** `dividedby/agent-research` itself; else `no` |
| `DEFAULT_BRANCH` | `main` \| `master` \| … |
| `PRIVATE_MARKERS` | private tokens (owner names, internal identifiers, private source names) to pass to the leak guard, if the repo is private; empty if fully public |

## Read first (fetch — do not guess)

- **The skill:** `dividedby/skills` → `skills/meta/apply-agent-research/SKILL.md`
  + `proposal-flow.md`. Self-contained: bundles its guard/gate under `lib/`,
  invoked by file path `python3 <skill-dir>/lib/cli.py`, **fetched fresh each run,
  never vendored** ([ADR 0008](../adr/0008-consumers-fetch-the-skill-fresh-not-vendored.md)).
- **The cross-repo contracts:** `docs/design/skill-request-flow.md` (demand) and
  `docs/design/skill-promotion-flow.md` (supply), plus ADRs
  [0006](../adr/0006-skill-request-demand-corroboration.md),
  [0010](../adr/0010-consumers-audit-local-skills-supply-side.md),
  [0011](../adr/0011-per-channel-proposal-caps.md).
- **The already-do-this baseline:** `docs/agents/installed-skills.md` +
  ADRs [0007](../adr/0007-already-do-this-baseline-includes-installed-skills.md),
  [0009](../adr/0009-skill-request-checks-existing-and-installed-skills.md). The
  baseline covers skills installed in the host's *global* environment, not just
  files under the repo; a remote run can't enumerate the install, so the host
  commits a snapshot the loop reads.
- **A reference workflow to adapt:** `dividedby/skills` →
  `.github/workflows/apply-agent-research.yml` + `.github/workflows/prompts/apply-agent-research.md`.
- **The target repo's own governance docs:** `CONTEXT.md`, `CLAUDE.md`,
  `docs/adr/` — the skill's ethos-fit oracle *and* already-do-this filter.

## What to build in `CONSUMER_REPO`

Start from the [harness skeleton](./proposal-loop-harness.md) (fetch-fresh,
`contents: read` / `issues: write`, off-the-hour cron + `workflow_dispatch`,
scoped tools, step-summary with the `total_cost_usd=…` cost-ledger line). Then
layer on the Consumer specifics:

1. **Fetch the skill fresh + hard-gate its guard.** Clone `dividedby/skills`
   shallow, `cp -R skills/meta/apply-agent-research` into `~/.claude/skills/`.
   Immediately **run the guard's unit tests as a hard gate**
   (`python3 -m unittest discover -s <skill-dir>/tests`) and confirm the seam runs —
   the gate (`cli.py gate`), the standalone guard (`cli.py sanitize`), and the
   **guarded filing path** (`cli.py file --help` / `cli.py comment --help`), which is
   how the loop files (step 7). **Never proceed on a broken guard.**
   The same fresh clone is also the **live published-skill catalog** the
   already-do-this / audit steps read (`skills/<bucket>/*/SKILL.md`,
   `.claude-plugin/plugin.json`) — no separate fetch.

2. **Knowledge input.**
   - `IS_KNOWLEDGE_SOURCE = no` → shallow-clone the **public mirror**
     `dividedby/agent-research-knowledge` (credential-free, read-only). Never
     clone the private `agent-research`.
   - `IS_KNOWLEDGE_SOURCE = yes` → read this repo's own `knowledge/` tree
     natively; **skip the mirror clone** and point the skill's `MIRROR_DIR` (or
     equivalent) at the local `knowledge/` path. Schedule **after** this repo's
     own synthesis run so it reads fresh knowledge.
   - Invoke Claude using **this repo's existing convention** (e.g. match
     `anthropics/claude-code-base-action` if its other workflows use it).

3. **Per-channel outputs ([ADR 0011](../adr/0011-per-channel-proposal-caps.md)) —
   at most one issue _per channel_ per run, zero fine.** Into the repo's **own**
   tracker (ensure each label idempotently in the workflow):
   - **self-improvement** (`source:agent-research`) — one agent-meta improvement
     from a KB note.
   - **skill-audit** (`source:skill-audit`) — the supply-side audit, step 4.

4. **Supply-side audit of local skills**
   ([ADR 0010](../adr/0010-consumers-audit-local-skills-supply-side.md)) — **only
   if this repo has local (non-published) skills; skip otherwise.** Enumerate each
   local skill and match it against the published catalog (the fresh clone) **and**
   `docs/agents/installed-skills.md`. Three verdicts:
   - **Redundant** (matches an existing skill) → a `source:skill-audit` candidate
     in this repo's own tracker: adopt the canonical skill, retire the local copy.
   - **Promotable** (no match **and** broadly useful per
     [ADR 0001](../adr/0001-buckets-cluster-by-user-intent.md)) → a
     `skill-promotion` offer (step 6).
   - **Repo-specific** → keep, no-op.

5. **`skill-request` demand channel** (`docs/design/skill-request-flow.md`) —
   when the KB mapping lands on a capability that *should* exist as a published
   skill but does not:
   - **Filter already-do-this first** ([ADR 0009](../adr/0009-skill-request-checks-existing-and-installed-skills.md)):
     match the candidate against the published catalog (fresh clone) **and**
     `docs/agents/installed-skills.md`. If either covers it, **do not file**.
   - `gh issue list --label skill-request --state open --repo dividedby/skills`,
     match on `<!-- capability: <slug> -->`. **No match** → file a new issue through
     the guarded path (`cli.py file --repo dividedby/skills --label skill-request
     --title … --body-file …`) following the full contract (capability generalized;
     the *specific, traceable* motivating KB note; why a published skill; what it
     does not duplicate; `CONSUMER_REPO`; the capability marker). **Match** → `+1 —
     also wanted by CONSUMER_REPO` via `cli.py comment --repo dividedby/skills
     --issue <n> --body-file …`, plus this repo's motivating knowledge. Apply the
     existing `skill-request` label; never create it.

6. **`skill-promotion` supply channel** (`docs/design/skill-promotion-flow.md`) —
   for each **promotable** local skill from step 4:
   - `gh issue list --label skill-promotion --state open --repo dividedby/skills`,
     match on `<!-- capability: <slug> -->`. **No match** → file a new
     `skill-promotion` issue via the guarded path (`cli.py file --repo
     dividedby/skills --label skill-promotion …`) (capability offered, generalized;
     why it clears general merit and is skill-shaped; a pointer to where the
     implementation lives — never a paste; not-already-covered; `CONSUMER_REPO`; the
     marker). **Match** → `+1 — also built by CONSUMER_REPO` via `cli.py comment`.
     Apply the existing `skill-promotion` label; never create it.

   Steps 5–6 write to `dividedby/skills`, so they use **`SKILLS_TRACKER_TOKEN`**,
   never the default `GITHUB_TOKEN` (own-repo scoped → 403). Each is its own
   per-channel ≤1 output.

7. **Leak guard on every filed body — enforced by the filing path, not by memory.**
   Every issue and +1 is filed through `cli.py file` / `cli.py comment`, which run
   the guard on the `title + body` and write to the tracker **only on ALLOW** — so
   no filed body (including the cross-repo ones, which land on a **public** tracker)
   can skip it. Wire the Consumer workflow to **disallow direct `gh issue create` /
   `gh issue comment`** (`--disallowedTools` on the `claude` invocation) so the
   guarded path is the only way to write a tracker. If the repo is private, pass
   `PRIVATE_MARKERS` to those calls (`--marker <name> --marker <name>`, repeatable)
   so any occurrence hard-blocks. The guard catches *structural* leaks otherwise; a
   private Consumer almost always has markers to add — and step 6 is the highest
   risk, since the thing being offered is the repo's own `SKILL.md`.

## Manual steps for the human (surface these — the agent cannot do them)

- **Create a fine-grained PAT**, least privilege: Repository access = **only**
  `dividedby/skills`; Permissions = `Issues: Read and write` (+ implied
  `Metadata: Read`); finite expiry. Store as the Actions secret
  `SKILLS_TRACKER_TOKEN` in `CONSUMER_REPO`. (One token covers **both**
  `skill-request` and `skill-promotion` — same repo, same scope.) Blast radius of
  a leak: file/comment issues on the public skills tracker, nothing more.
- **Ensure `CLAUDE_CODE_OAUTH_TOKEN`** exists (a repo already running Claude in
  Actions has it — reuse, don't re-add).
- **Create a second fine-grained PAT for the cost ledger**, least privilege:
  Repository access = **only** `CONSUMER_REPO`; Permissions = `Actions: Read`
  (+ implied `Metadata: Read`); finite expiry. Hand it to the `dividedby/agent-research`
  owner to store there as the secret `<CONSUMER>_ACTIONS_TOKEN` — it lives in the
  **hub** repo, not in `CONSUMER_REPO`, because the hub uses it to read this
  Consumer's run logs and scrape the `total_cost_usd=…` summary line. This is
  **distinct** from `SKILLS_TRACKER_TOKEN` (Issues:rw, can't read Actions logs):
  least privilege **per channel**.
  - **`<CONSUMER>` is a deliberate, stable short-name, not the repo slug.** The hub
    can't mechanically derive it, so it stores the secret under exactly the literal
    name you choose — e.g. `goodreads-bot` registers as `GOODREADS_ACTIONS_TOKEN`
    (the `-bot` is dropped). Pick the short-name once and keep it fixed; it's the
    literal secret name on the hub side.
  - **Hub-side counterpart (for the agent-research owner).** Onboarding into the
    ledger is three mechanical edits in `dividedby/agent-research`: add a
    `RepoSurface` to the `COST_SURFACE` registry in `kb_afk/cost_ledger.py`, add the
    matching secret-passthrough line to `.github/workflows/cost-ledger.yml`, and add
    a docs row. The procedure is documented there in `docs/cost-tracking.md`
    ("Onboarding a new Consumer"); follow that rather than this summary if they
    diverge. Code can land **ahead of** the token — an unset `<CONSUMER>_ACTIONS_TOKEN`
    scrapes 0 rows for the repo (no failure), so provisioning order is flexible.
    (`agent-research` is private; this pointer is for the owner, not a read the
    onboarding agent needs — the consumer-side contract above is self-sufficient.)

## Verify

`workflow_dispatch` a manual run. Confirm it: clones the mirror (or reads native
knowledge); runs the guard tests green; files **≤1 per channel** into this repo's
own tracker (or prints `SKIPPED: <channel>: …`); and — if warranted — files-or-+1's
≤1 `skill-request` and/or ≤1 `skill-promotion` in `dividedby/skills`. Confirm the
step summary carries the `total_cost_usd=…  duration_ms=…  num_turns=…` ledger
line (present even on a failed run). Watch the run; report the issue links.

## Guardrails (do not violate)

- The loop **proposes, never applies**: no edits, commits, or PRs — only issues.
  At most one issue **per channel** per run; zero is fine.
- Every filed body passes the real leak guard; no private content reaches a public
  tracker. Keep prose generalized regardless.
- Duplicate `skill-request`s and `skill-promotion`s **aggregate** (+1); they never
  dedup-suppress.
- `dividedby/skills` owns the `skill-request` and `skill-promotion` labels;
  Consumers apply, never create. The repo owns its own `source:*` labels.
- The public mirror is read-only; never write back to it or to `agent-research`.
