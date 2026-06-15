---
name: setup-dividedby-skills
description: Install the dividedby conventions into a target repo in one idempotent pass — scaffold the docs/agents convention files and the CLAUDE.md Conventions block, create the Idea Inbox issue, reconcile GitHub labels to match docs/agents/labels.md, and onboard the branching/merge policy. Every GitHub mutation is gated behind an explicit report-then-confirm step. Manual/slash invocation only.
disable-model-invocation: true
---

# Setup dividedby/skills conventions

One idempotent pass that installs this ecosystem's cross-cutting conventions into a **target repo**. Every network mutation — label create/edit, merge-setting PATCH, Inbox issue creation, default-branch change — is preceded by a plan you must explicitly confirm. Nothing is written or mutated until you approve.

**Seam with `project-claude-config`:** that skill owns the Claude harness (`.claude/settings.json`, hooks) and the instruction files (`CLAUDE.md`/`AGENTS.md`). This skill owns the issue-tracker/labels/domain/idea-inbox conventions and the GitHub repo-level settings (labels, branching/merge mechanics). Run `project-claude-config` first on a greenfield repo — this skill then wires in what `project-claude-config` leaves as stubs. See [ADR 0023](../../docs/adr/0023-setup-dividedby-skills-vs-project-claude-config-seam.md).

---

## Before starting

Identify the target repo:
- `cd` into the clone, or set the target explicitly (`gh repo view` to confirm owner/name).
- Read `~/.claude/branching-flow.md` now — it is the sole source of truth for merge mechanics and role classification. Do not proceed without it.
- Read the canonical convention docs from **`dividedby/skills`** (not cached copies):
  - `docs/agents/issue-tracker.md`
  - `docs/agents/labels.md`
  - `docs/agents/domain.md`
  - `docs/agents/idea-inbox.md`
  - `CLAUDE.md` lines 11–52 (the `## Conventions` block)

These are the authoritative sources. Adapt repo-specific references (e.g. the Inbox issue URL, the repo name in the Intake line) when porting content — do not copy raw.

---

## Step 1 — Detect (what already exists)

Dispatch Explore to report on everything **except labels** (labels are diffed directly — see below):

- **Convention docs:** does `docs/agents/` exist? Which of `issue-tracker.md`, `labels.md`, `domain.md`, `idea-inbox.md` are present?
- **CLAUDE.md / AGENTS.md:** does a `## Conventions` block exist? What sections does it contain?
- **Idea Inbox issue:** search open+closed issues for `label:idea-inbox`. Note the issue number if found.
- **Branching/merge settings:** `gh api repos/{owner}/{repo} --jq '{allow_squash_merge,allow_rebase_merge,allow_merge_commit,delete_branch_on_merge,default_branch}'`. Compare against universal mechanics. Check whether this repo is already listed in `~/.claude/branching-flow.md`.

**Labels — diff directly on the lead, do not delegate.** Label drift is a deterministic set/string comparison, and a delegated prose summary miscounts (it'll report the wrong label count). Run the live list yourself and diff it against the canonical table in `docs/agents/labels.md` — compare exact name/color/description strings, not impressions:

```
gh label list --repo {owner}/{repo} --limit 100 --json name,color,description --jq 'sort_by(.name)[] | "\(.name)\t\(.color)\t\(.description)"'
```

Report: (a) canonical labels **missing** from the repo, (b) labels present with color/description **drift** (canonical vs actual), (c) **stock** labels still present (`documentation`, `duplicate`, `good first issue`, `help wanted`, `invalid`, `question`). Honor the tiering rule in `labels.md` (CORE everywhere; LOOP/NETWORK only on full-tier repos — a repo carrying any `source:*` label is full-tier).

Condense findings to a state summary; do not dump raw output.

---

## Step 2 — Draft the plan

From the detect report, build a per-concern action list. Use a three-state posture for each item:

- **create** — missing; will be created from scratch.
- **update** — present but drifted; will be updated in place.
- **skip** — already correct; no action.

### Concern A — Convention docs

For each of `docs/agents/{issue-tracker,labels,domain,idea-inbox}.md`:
- **create** from the dividedby/skills canonical source, adapting repo-specific references.
- **update** if present but stale (note what changed).
- **skip** if already current.

### Concern B — CLAUDE.md / AGENTS.md Conventions block

Locate the `## Conventions` heading in the target's instruction file.
- **create** if absent: insert the block (ported from `dividedby/skills CLAUDE.md:11–52`) with adapted references — correct repo name in the Inbox link, `docs/agents/*.md` paths relative to the target.
- **update** if the block exists but is missing sections or has stale links.
- **skip** if complete and current.

### Concern C — Idea Inbox issue

- **create** if no `idea-inbox`-labeled issue exists: body is exactly the skeleton from `docs/agents/idea-inbox.md` — breadcrumb comment on line 1, then `## Ideas` / `✅ Actioned` headers. Label: `idea-inbox`.
- **skip** if already present.

### Concern D — GitHub labels

For each label in `docs/agents/labels.md`:
- **create** if absent from the repo.
- **update** (name/color/description) if present but drifted.
- **skip** if correct.
- **delete** stock labels (`documentation`, `duplicate`, `good first issue`, `help wanted`, `invalid`, `question`) after re-labeling any issues that carry them.

Note: `bug` and `enhancement` likely exist as GitHub defaults with wrong colors — treat as **update**, not create.

Whether to apply LOOP/NETWORK labels depends on whether the target repo runs proposal loops. Ask if not determinable from detect output.

### Concern E — Branching/merge policy

From `~/.claude/branching-flow.md`:
- **Classify role:** library/tool (trunk-based, default `main`) or deployed app (two-branch, default `staging`). Use the criteria from `branching-flow.md` — two-branch only when a real staging environment exists. Ask if ambiguous.
- **`branching-flow.md` entry:** if the target repo is not listed, add it under the appropriate tier. This is a local file edit, not a network mutation — but still surface it in the plan.
- **Merge settings PATCH:** if any of `allow_squash_merge`, `allow_rebase_merge`, `allow_merge_commit`, `delete_branch_on_merge` diverges from the universal mechanics, plan a PATCH.
- **Default branch:** if it does not match the role (e.g. `main` on a deployed app, or `staging` on a library), plan a default-branch change.

---

## Step 3 — Report and confirm (HITL gate — mandatory)

**Show the full plan before any network mutation or file write.**

Present it as a structured list, grouped by concern (A–E), with one line per action showing posture (create / update / skip) and a brief what/why. Flag any destructive actions (label deletes, default-branch change) explicitly.

**Do not proceed until the user types explicit confirmation** (e.g. "go", "approved", "yes"). A non-response or an ambiguous reply is not approval. If the user modifies the plan, update the action list before proceeding.

This gate is non-negotiable — this skill mutates someone's repo over the network.

---

## Step 4 — Execute

Execute the approved plan concern by concern. Idempotency rules:

**A — Convention docs:** write files to `docs/agents/` in the target. Adapt every dividedby/skills-specific reference (Inbox issue URL, the repo's own name/link) to the target. Do not copy stale literal content; re-read the canonical source at execution time.

**B — CLAUDE.md Conventions block:** insert or patch the block. The block's content is structural (headings and pointer lines to `docs/agents/*.md`); it should not contain the full prose of the docs — just the same-level-of-abstraction stubs that `dividedby/skills CLAUDE.md:11–52` uses.

**C — Idea Inbox issue:**

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

After creation, record the issue number; update the Intake line in the CLAUDE.md Conventions block with the correct URL.

**D — GitHub labels:**

For each **create**:
```
gh label create "<name>" --color "<hex>" --description "<desc>"
```

For each **update** (color/description drift):
```
gh label edit "<name>" --color "<hex>" --description "<desc>"
```

For stock label **deletes** — before deleting, check whether any open issues carry the label; if so, re-label them to the appropriate convention label first. Then:
```
gh label delete "<name>" --yes
```

**E — Branching/merge policy:**

Edit `~/.claude/branching-flow.md` to add the target repo under its tier (local file write, no confirmation gate needed since it was in the plan).

Apply the universal merge settings:
```
gh api -X PATCH repos/{owner}/{repo} \
  -F allow_squash_merge=false \
  -F allow_rebase_merge=false \
  -F allow_merge_commit=true \
  -F delete_branch_on_merge=true
```

If a default-branch change is approved, set it:
```
gh api -X PATCH repos/{owner}/{repo} -f default_branch=<branch>
```

---

## Step 5 — Verify

After execution, re-run the key checks:

- `gh label list --limit 100 --json name,color,description` — confirm label set matches `docs/agents/labels.md` with no drift.
- `gh api repos/{owner}/{repo} --jq '{allow_squash_merge,allow_rebase_merge,allow_merge_commit,delete_branch_on_merge,default_branch}'` — confirm universal mechanics applied.
- Confirm `docs/agents/` holds all four convention files.
- Confirm the CLAUDE.md Conventions block is present and the Inbox link resolves.

Report a short summary: what was created, what was updated, what was skipped. If anything diverges, surface it — do not silently leave drift.

---

## Idempotency guarantee

Re-running this skill on a fully-set-up repo must produce no mutations. Every action check uses the current live state (re-detect at run time, never cache). "Skip" should be the dominant outcome on a second pass.
