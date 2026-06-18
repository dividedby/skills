---
name: setup-dividedby-skills
description: Install the dividedby conventions on top of setup-matt-pocock-skills — size labels, intake/idea-inbox, branching policy, the Conventions block, and HITL verification gates. Every network mutation is gated behind an explicit confirm step. Manual/slash invocation only.
disable-model-invocation: true
---

# Setup dividedby/skills conventions

A **composed** pass — run **after** `setup-matt-pocock-skills` — that layers the dividedby-specific conventions onto the shared scaffold Matt's skill already installed.

**What Matt's skill gives you:** issue tracker, triage labels (incl. `needs-info`), domain doc layout, and the `## Agent skills` instruction block.

**What this skill adds:** `size:*` labels, intake/idea-inbox, branching/merge policy, the `## Conventions` block (incl. skill-editorial-intent and HITL/verification gates), and reconciliation of the label set to the dividedby CORE posture (which suppresses `needs-info`).

Every network mutation — label create/edit/delete, merge-setting PATCH, Inbox issue creation, default-branch change — is preceded by a plan you must explicitly confirm. Nothing is written or mutated until you approve.

**Seam with `project-claude-config`:** that skill owns the Claude harness (`.claude/settings.json`, hooks) and the instruction files (`CLAUDE.md`/`AGENTS.md`). This skill owns the issue-tracker/labels/idea-inbox conventions and GitHub repo-level settings. Run `project-claude-config` first on a greenfield repo, then `setup-matt-pocock-skills`, then this skill. See [ADR 0023](../../docs/adr/0023-setup-dividedby-skills-vs-project-claude-config-seam.md).

---

## Before starting

Identify the target repo:
- `cd` into the clone, or set the target explicitly (`gh repo view` to confirm owner/name).
- Read `~/.claude/branching-flow.md` — sole source of truth for merge mechanics and role classification. Do not proceed without it.
- Read the canonical convention docs from **`dividedby/skills`** (not cached copies):
  - `docs/agents/labels.md`
  - `docs/agents/idea-inbox.md`
  - `CLAUDE.md` lines 11–52 (the `## Conventions` block)

These are authoritative. Adapt repo-specific references (Inbox issue URL, repo name) when porting content — do not copy raw.

---

## Step 1 — Detect (what already exists)

Dispatch Explore to report on:

- **CLAUDE.md / AGENTS.md:** does a `## Conventions` block exist? Which sections?
- **Idea Inbox issue:** search open+closed issues for `label:idea-inbox`. Note the issue number if found.
- **Branching/merge settings:** `gh api repos/{owner}/{repo} --jq '{allow_squash_merge,allow_rebase_merge,allow_merge_commit,delete_branch_on_merge,default_branch}'`. Compare against universal mechanics. Check whether this repo is already listed in `~/.claude/branching-flow.md`.

**Labels — diff directly on the lead, do not delegate.** Run the live list and diff it against `docs/agents/labels.md`:

```
gh label list --repo {owner}/{repo} --limit 100 --json name,color,description --jq 'sort_by(.name)[] | "\(.name)\t\(.color)\t\(.description)"'
```

Report:
- CORE labels (State, Category, Size) missing or drifted
- `needs-info` present (it must be **removed** — Matt's setup installs it; the dividedby posture suppresses it)
- CORE `idea-inbox` label missing or drifted
- Stock labels still present (`documentation`, `duplicate`, `good first issue`, `help wanted`, `invalid`, `question`)

Condense findings to a state summary; do not dump raw output.

---

## Step 2 — Draft the plan

From the detect report, build a per-concern action list with a three-state posture per item: **create**, **update**, or **skip**.

### Concern A — CLAUDE.md / AGENTS.md Conventions block

Locate the `## Conventions` heading in the target's instruction file.
- **create** if absent: insert the block (ported from `dividedby/skills CLAUDE.md:11–52`) with adapted references — correct repo name in the Inbox link, `docs/agents/*.md` paths relative to the target.
- **update** if the block exists but is missing sections or has stale links.
- **skip** if complete and current.

The block includes: Issue tracker, Triage labels, Domain docs, Installed skills (if relevant), Intake convention (with the live Inbox URL), Skill editorial intent, and HITL/verification gate posture.

### Concern B — Idea Inbox issue

- **create** if no `idea-inbox`-labeled issue exists: body is exactly the skeleton from `docs/agents/idea-inbox.md` — breadcrumb comment on line 1, then `## Ideas` / `✅ Actioned` headers. Label: `idea-inbox`.
- **skip** if already present.

### Concern C — GitHub labels

Apply the dividedby CORE label set from `docs/agents/labels.md` — State, Category, and Size tiers only. Do **not** install LOOP/NETWORK or CHANNELS labels.

For each CORE label:
- **create** if absent.
- **update** (name/color/description) if present but drifted.
- **skip** if correct.

Additionally:
- **delete `needs-info`** — Matt's setup installs it as a canonical role; the dividedby posture suppresses it. Before deleting, re-label any open issues that carry it to `needs-triage`.
- **delete** stock labels (`documentation`, `duplicate`, `good first issue`, `help wanted`, `invalid`, `question`) after re-labeling any issues that carry them.

Note: `bug` and `enhancement` likely exist as GitHub defaults with wrong colors — treat as **update**, not create.

### Concern D — Branching/merge policy

From `~/.claude/branching-flow.md`:
- **Classify role:** library/tool (trunk-based, default `main`) or deployed app (two-branch, default `staging`). Ask if ambiguous.
- **`branching-flow.md` entry:** if the target repo is not listed, add it under the appropriate tier (local file edit — still surface it in the plan).
- **Merge settings PATCH:** if any of `allow_squash_merge`, `allow_rebase_merge`, `allow_merge_commit`, `delete_branch_on_merge` diverges from the universal mechanics, plan a PATCH.
- **Default branch:** if it does not match the role, plan a default-branch change.

---

## Step 3 — Report and confirm (HITL gate — mandatory)

**Show the full plan before any network mutation or file write.**

Present it as a structured list, grouped by concern (A–D), with one line per action showing posture (create / update / skip / delete) and a brief what/why. Flag destructive actions (label deletes, `needs-info` removal, default-branch change) explicitly.

**Do not proceed until the user types explicit confirmation** (e.g. "go", "approved", "yes"). A non-response or an ambiguous reply is not approval. If the user modifies the plan, update the action list before proceeding.

This gate is non-negotiable — this skill mutates someone's repo over the network.

---

## Step 4 — Execute

Execute the approved plan concern by concern.

**A — Conventions block:** insert or patch the block. The block's content is structural — headings and pointer lines to `docs/agents/*.md`; same level of abstraction as `dividedby/skills CLAUDE.md:11–52`. Do not embed the full prose of the docs.

**B — Idea Inbox issue:**

```
gh issue create \
  --title "Idea Inbox" \
  --body-file /tmp/idea-inbox-body.md \
  --label idea-inbox
```

Write the body file first (Write tool). Body template:

```
<!-- agent-protocol: drain=docs/agents/idea-inbox.md -->

## Ideas

## ✅ Actioned
```

After creation, record the issue number; update the Intake line in the Conventions block with the correct URL.

**C — GitHub labels:**

For each **create**:
```
gh label create "<name>" --color "<hex>" --description "<desc>"
```

For each **update**:
```
gh label edit "<name>" --color "<hex>" --description "<desc>"
```

For `needs-info` and stock label **deletes** — check for open issues carrying the label; re-label them first. Then:
```
gh label delete "<name>" --yes
```

**D — Branching/merge policy:**

Edit `~/.claude/branching-flow.md` to add the target repo under its tier (local file write — no separate confirmation needed since it was in the plan).

Apply the universal merge settings:
```
gh api -X PATCH repos/{owner}/{repo} \
  -F allow_squash_merge=false \
  -F allow_rebase_merge=false \
  -F allow_merge_commit=true \
  -F delete_branch_on_merge=true
```

If a default-branch change is approved:
```
gh api -X PATCH repos/{owner}/{repo} -f default_branch=<branch>
```

---

## Step 5 — Verify

After execution, re-run the key checks:

- `gh label list --limit 100 --json name,color,description` — confirm CORE label set matches `docs/agents/labels.md` with no drift; confirm `needs-info` is absent.
- `gh api repos/{owner}/{repo} --jq '{allow_squash_merge,allow_rebase_merge,allow_merge_commit,delete_branch_on_merge,default_branch}'` — confirm universal mechanics applied.
- Confirm the Conventions block is present and the Inbox link resolves.

Report a short summary: what was created, what was updated, what was skipped. Surface any drift — do not silently leave it.

---

## Idempotency guarantee

Re-running this skill on a fully-set-up repo must produce no mutations. Every action check uses the current live state (re-detect at run time, never cache). "Skip" should be the dominant outcome on a second pass.
