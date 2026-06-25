---
name: setup-dividedby-skills
description: Install the dividedby conventions on top of setup-matt-pocock-skills — size labels, intake/idea-inbox, branching policy, the Conventions block, and HITL verification gates. Every network mutation is gated behind an explicit confirm step. Manual/slash invocation only.
disable-model-invocation: true
---

# Setup dividedby/skills conventions

A **composed** pass — run **after** `setup-matt-pocock-skills` — that layers the dividedby-specific conventions onto the shared scaffold Matt's skill already installed.

**What Matt's skill gives you:** issue tracker, triage labels (incl. `needs-info`), domain doc layout, and the `## Agent skills` instruction block.

**What this skill adds:** `size:*` labels, intake/idea-inbox, branching/merge policy, the `## Conventions` block, and reconciliation of the label set and label-convention doc to the dividedby CORE posture.

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
  - `docs/agents/changelog-guideline.md` (the fleet changelog rubric — Concern G)
  - `harness/changelog-health/enrolled-repos.txt` (the evaluator's enrollment list — Concern G)
  - `CLAUDE.md` lines 11–52 (the `## Conventions` block)

These are authoritative. Adapt repo-specific references (Inbox issue URL, repo name) when porting content — do not copy raw.

---

## Step 1 — Detect (what already exists)

Dispatch Explore to report on:

- **CLAUDE.md / AGENTS.md:** does a `## Conventions` block exist? Which sections? Does the Triage labels pointer reference `docs/agents/triage-labels.md` or `docs/agents/labels.md`?
- **Idea Inbox issue:** search open+closed issues for `label:idea-inbox`. Note the issue number if found.
- **`docs/agents/triage-labels.md`:** does it exist? Does it contain the dividedby CORE/LOOP-NETWORK/CHANNELS tiering structure, or is it Matt's version?
- **`docs/agents/idea-inbox.md`:** does it exist?
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

**Stale cross-reference scan.** After the label diff, read the target's `docs/agents/*.md` files and the `## Conventions` block in the instruction file. Search for:
- any reference to `needs-info`
- Matt-specific role→label wording that the dividedby convention removes

Record each hit (file + line) in the detect report. These will be reconciled in Concern D (triage-labels.md overwrite) and Concern A (Conventions block update).

Condense findings to a state summary; do not dump raw output.

---

## Convention classification

Every convention this skill manages is classified as one of two kinds:

| Convention | Classification | Rationale |
|---|---|---|
| C — GitHub label name / color / description | **convention-only** | Purely mechanical; the canonical values are specified in `docs/agents/labels.md` with no judgment required. |
| C — `needs-info` removal | **convention-only** | The dividedby posture unconditionally suppresses `needs-info`; no judgment call. |
| C — stock label deletion | **convention-only** | Stock labels are unconditionally removed; canonical list is fixed. |
| D — label-doc file layout (single vs split, full vs pointer) | **convention-only** | File-name and single-file-vs-split is a pure layout convention. The correct form is `docs/agents/triage-labels.md` with full dividedby content. No judgment involved. |
| A — Conventions block content | **convention-only** | The block structure and pointer targets are prescribed; adapt repo-specific references only. |
| E — `docs/agents/idea-inbox.md` creation | **convention-only** | Seeded from a fixed template; repo-name substitution only. |
| B — Idea Inbox issue | **convention-only** | Fixed body template; repo-name substitution only. |
| F — branching role classification (library vs app) | **judgment-bearing** | Role determines default branch and merge mechanics; requires human judgment about the repo's purpose. |
| F — default-branch change | **judgment-bearing** | Destructive and role-dependent; always requires explicit confirmation. |
| G — CHANGELOG.md scaffold + git-history seed (new repo) | **judgment-bearing** | Which surfaces to track and which git-log changes are notable both require human judgment; the draft must be reviewed before writing. |
| G — CHANGELOG.md KaC 2.0.0 migration (existing repo, mechanical) | **convention-only** | URL bump, missing `## [Unreleased]` insert, dead 1.x anchor removal — fixed transforms, never touching past entry content. |
| G — `docs/agents/changelog-guideline.md` copy | **convention-only** | Canonical doc copied with ref adaptation only; no judgment. |
| G — `enrolled-repos.txt` enrollment | **convention-only** | Append one `owner/repo` line; fixed format, no judgment. |

**force-canonical eligibility:** only convention-only items may be auto-applied by force-canonical mode. judgment-bearing items always prompt, even in force-canonical mode — they are never auto-applied.

New conventions added to this skill must declare which classification they belong to in this table before being implemented.

---

## Step 2 — Draft the plan

From the detect report, build a per-concern action list with a four-state posture per item: **create**, **update**, **skip**, or **must-fix**.

**State definitions:**
- **create** — the item does not exist; will be created.
- **update** — the item exists but is drifted from canonical in a routine way; will be reconciled.
- **skip** — the item is already canonical. A skip means already canonical, never "non-canonical but left alone."
- **must-fix** — a *known* non-canonical form that cannot resolve to skip. The fix is destructive (delete a stray file, rewrite a pointer, overwrite Matt's version) and requires confirmation before applying. Surfaces the exact diff/destructive change so the user knows precisely what will happen.

### Concern A — CLAUDE.md / AGENTS.md Conventions block

Locate the `## Conventions` heading in the target's instruction file.
- **create** if absent: insert the block (ported from `dividedby/skills CLAUDE.md:11–52`) with adapted references — correct repo name in the Inbox link, `docs/agents/*.md` paths relative to the target.
- **update** if the block exists but is missing sections or has stale links.
- **skip** if complete and current.

The block includes: Issue tracker, Triage labels, Domain docs, Installed skills (where applicable), Skill editorial intent (skills repo only), and Intake convention (with the live Inbox URL).

The **Triage labels** pointer in the Conventions block must point at `docs/agents/triage-labels.md` (Matt's filename, overwritten with dividedby content by Concern D — see below). Do **not** point at `docs/agents/labels.md`; that file does not exist in the target. If the block was seeded with a `docs/agents/labels.md` reference, update it to `docs/agents/triage-labels.md`.

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

### Concern D — `docs/agents/triage-labels.md` (dividedby content)

Matt's skill creates this file with content from his template (which includes `needs-info` and uses his role→label map). Overwrite it with the dividedby label convention, seeded from `dividedby/skills docs/agents/labels.md`, adapting repo-specific references (replace `dividedby/skills` with the target repo name in the CHANNELS note).

Note: the seeded doc is the **full convention reference** — it describes all tiers (CORE, LOOP-NETWORK, CHANNELS). Only CORE labels are actually created on GitHub (Concern C). A reader should not infer that LOOP/CHANNELS labels were installed.

Also reconcile any stale references found in the detect scan: if `docs/agents/issue-tracker.md`, `docs/agents/domain.md`, or any other file in `docs/agents/` contains `needs-info` or Matt-specific role→label wording, update those lines to match the dividedby convention. Surface each such edit in the HITL plan before executing.

**Known drift shapes (all resolve to must-fix, not skip):**

The following forms are *known* non-canonical. They cannot resolve to skip — each triggers **must-fix**, which surfaces the exact destructive diff before applying:

1. **Two-file split** — both `docs/agents/labels.md` and `docs/agents/triage-labels.md` exist. The stray `labels.md` must be deleted after all refs are retargeted to `triage-labels.md`. Surface: "will delete `docs/agents/labels.md` (stray file) and retarget N references."
2. **Short-form / pointer `triage-labels.md`** — the file exists but is a short-form stub or pointer (does not contain the full dividedby CORE/LOOP-NETWORK/CHANNELS tiering structure). Surface: "will overwrite `docs/agents/triage-labels.md` with full canonical content."
3. **`labels.md`-only repo** — only `docs/agents/labels.md` exists; `triage-labels.md` is absent. Surface: "will rename/copy content to `docs/agents/triage-labels.md` and delete `docs/agents/labels.md`."

For each must-fix item, the plan step must state: the exact file(s) being deleted or overwritten, the reason (which drift shape), and the proposed replacement content summary. The user must confirm before any write or delete executes.

**Routine states:**
- **update** if the file exists but does not contain the dividedby CORE/LOOP-NETWORK/CHANNELS tiering structure (i.e. it's Matt's version) — this is a must-fix unless covered by a drift shape above; treat as must-fix with overwrite diff surfaced.
- **skip** if the file already carries the dividedby content (idempotent re-run). skip means already canonical — never a tolerated deviation.

This is a file write in the target repo, not a network mutation — but surface it in the plan so the user can approve.

### Concern E — `docs/agents/idea-inbox.md`

The Conventions block's Intake pointer references this file; Concern B creates the Inbox *issue*, but the *doc* must also exist.

- **create** if `docs/agents/idea-inbox.md` is absent: seed from `dividedby/skills docs/agents/idea-inbox.md`, adapting the CHANNELS note (replace `dividedby/skills` with the target repo name) and any other repo-specific references.
- **skip** if already present.

### Concern F — Branching/merge policy

From `~/.claude/branching-flow.md`:
- **Classify role:** library/tool (trunk-based, default `main`) or deployed app (two-branch, default `staging`). Ask if ambiguous.
- **`branching-flow.md` entry:** if the target repo is not listed, add it under the appropriate tier (local file edit — still surface it in the plan).
- **Merge settings PATCH:** if any of `allow_squash_merge`, `allow_rebase_merge`, `allow_merge_commit`, `delete_branch_on_merge` diverges from the universal mechanics, plan a PATCH.
- **Default branch:** if it does not match the role, plan a default-branch change.

### Concern G — Changelog

Ensures the target repo carries a conforming `CHANGELOG.md`, the fleet changelog standards doc, and is enrolled in the centralized [changelog-health evaluator](../../../.github/workflows/changelog-health.yml). Three sub-steps — always plan in order (G1 → G2 → G3).

**G1 — `CHANGELOG.md`.** Detect against the [fleet rubric](../../../docs/agents/changelog-guideline.md): does the file exist? does the header contain `keepachangelog.com/en/2.0.0/`? is there exactly one `## [Unreleased]` and is it the first version section? any `keepachangelog.com/en/1.` URL? any dead 1.x FAQ anchor (`#why-…`/`#how-…`/`#what-…`)?
- **create** (absent) — *judgment-bearing.* Prompt the maintainer for the tracked surface(s) the changelog records; scaffold the canonical KaC-2.0.0 header (based-on-2.0.0 line + surfaces line + `## [Unreleased]`); run `git log --oneline --stat` and draft `## [Unreleased]` entries across the six categories in consumer voice (label the draft "review against rule 1 — notable-only"); present the full draft for HITL edit before writing. Edge case — if the repo has **no** `## [x.y.z]` semver header (date-grouped/non-versioned, e.g. infra per its ADR 0001), prompt before adding `## [Unreleased]` rather than forcing it.
- **must-fix** (exists but fails a check) — *convention-only* (force-canonical eligible). Surface each violation with its fix: 1.x URL → `…/en/2.0.0/`; missing `## [Unreleased]` → insert after the header block; dead 1.x anchor → remove/rewrite; no KaC reference at all (e.g. moodreader) → add the based-on-2.0.0 header line + `## [Unreleased]` without touching existing dated entries. **Never rewrite past entry content — structure/formatting only.**
- **skip** — passes all four checks.

**G2 — `docs/agents/changelog-guideline.md`.** Read the canonical from `dividedby/skills` (already read in Before starting). Adapt refs (relative ADR paths → absolute GitHub URLs; `#457` and similar → their URLs), then write to the target's `docs/agents/`.
- **create** if absent.
- **skip** if already present (consistent with `idea-inbox.md`; the evaluator catches content drift).

**G3 — Enrollment.** Read `~/repos/skills/harness/changelog-health/enrolled-repos.txt`.
- **create** if `dividedby/<target>` is absent: append the line, then print `git -C ~/repos/skills diff harness/changelog-health/enrolled-repos.txt` and remind the maintainer to commit it + open a skills PR before the next evaluator run (Thursday 01:33 UTC). **Do not run git mutations in the skills repo** — the maintainer commits.
- **skip** if `dividedby/<target>` is already present.

---

## Step 3 — Report and confirm (HITL gate — mandatory)

**Show the full plan before any network mutation or file write.**

Present it as a structured list, grouped by concern (A–G), with one line per action showing posture (create / update / skip / must-fix / delete) and a brief what/why. Flag destructive actions (label deletes, `needs-info` removal, default-branch change) explicitly.

For each **must-fix** item: include the exact destructive diff inline — what file will be deleted or overwritten, what the replacement is, and which drift shape triggered it. Do not collapse must-fix items into a generic "will fix drift" line.

**force-canonical mode (opt-in):** If the user invokes this skill with `force-canonical` (e.g. "run setup-dividedby-skills with force-canonical"), skip per-item confirmation prompts for all must-fix items that are **convention-only** and apply them in a single batch. The plan is still shown first (one presentation, then "applying all must-fix items without per-item prompts"). judgment-bearing items (branching role, default-branch changes) always prompt even in force-canonical mode — they are never auto-applied regardless of mode.

**Default mode (propose-only):** Each must-fix item requires explicit per-item confirmation. The user may approve, skip, or modify any individual item.

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

**D — `docs/agents/triage-labels.md`:**

Read `dividedby/skills docs/agents/labels.md` (already read in Before starting). Adapt it: replace `dividedby/skills` with the target repo name in the CHANNELS ownership note. Write the adapted content to `docs/agents/triage-labels.md` in the target, overwriting Matt's version. This is a local file write (target clone) — no network call.

Also apply any stale-reference fixes identified in the detect scan: update `needs-info` references and Matt-specific role→label wording in any `docs/agents/*.md` file that carries them.

**E — `docs/agents/idea-inbox.md`:**

Read `dividedby/skills docs/agents/idea-inbox.md` (already read in Before starting). Adapt it: replace `dividedby/skills` with the target repo name if referenced. Write the adapted content to `docs/agents/idea-inbox.md` in the target. This is a local file write — no network call.

**F — Branching/merge policy:**

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

**G — Changelog:** apply G1 → G2 → G3 in order. All three are local file writes (no network mutation).

- **G1 — `CHANGELOG.md`:** for **create**, write the HITL-approved draft to the target's `CHANGELOG.md`. For **must-fix**, apply only the surfaced structural fixes (URL bump / `## [Unreleased]` insert / dead-anchor removal / header add) — never edit past entry text.
- **G2 — `docs/agents/changelog-guideline.md`:** write the ref-adapted canonical doc to the target's `docs/agents/` (create only; skip if present).
- **G3 — Enrollment:** append `dividedby/<target>` to `~/repos/skills/harness/changelog-health/enrolled-repos.txt`, then:
  ```
  git -C ~/repos/skills diff harness/changelog-health/enrolled-repos.txt
  ```
  Print the diff and remind the maintainer: **commit it and open a skills PR before the next evaluator run (Thursday 01:33 UTC)** — this skill does not commit or push the skills repo.

---

## Step 5 — Verify

After execution, re-run the key checks:

- `gh label list --limit 100 --json name,color,description` — confirm CORE label set matches `dividedby/skills docs/agents/labels.md` (the authoritative source) with no drift; confirm `needs-info` is absent. Confirm `docs/agents/triage-labels.md` in the target contains the dividedby CORE/LOOP-NETWORK/CHANNELS tiering structure (not Matt's version).
- `gh api repos/{owner}/{repo} --jq '{allow_squash_merge,allow_rebase_merge,allow_merge_commit,delete_branch_on_merge,default_branch}'` — confirm universal mechanics applied.
- Confirm the Conventions block is present, the Inbox link resolves, and the Triage labels pointer references `docs/agents/triage-labels.md` (not `docs/agents/labels.md`).
- Confirm `docs/agents/idea-inbox.md` exists in the target.
- **G1:** `CHANGELOG.md` passes the four conformance checks — KaC `…/en/2.0.0/` URL, exactly one `## [Unreleased]` as the first version section, no `…/en/1.` URL, no dead 1.x FAQ anchor.
- **G2:** `docs/agents/changelog-guideline.md` is present in the target.
- **G3:** `dividedby/<target>` is present in `~/repos/skills/harness/changelog-health/enrolled-repos.txt` — and if just appended, re-surface the **pending skills PR** so it isn't forgotten (the repo isn't actually enrolled until that PR merges).

Report a short summary: what was created, what was updated, what was skipped. Surface any drift — do not silently leave it.

---

## Idempotency guarantee

Re-running this skill on a fully-set-up repo must produce no mutations. Every action check uses the current live state (re-detect at run time, never cache). "Skip" should be the dominant outcome on a second pass.
