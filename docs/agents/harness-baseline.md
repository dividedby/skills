# Harness Baseline

The canonical definition of a fully-onboarded `dividedby` repo, used by the
cross-repo divergence scan (epic #325) to classify every repo and drive
remediation. Nothing here is invented — every item traces to an actual output
of the composed onboarding skill set (`setup-dividedby-skills` plus the skills
it composes on or expects: `project-claude-config`, `setup-matt-pocock-skills`),
or to ADR 0024.

---

## Applicability bar

**A repo should carry the full harness when it is the regular workplace for
human+agent collaboration** — meaning it receives issues, is triaged by agents,
or runs any proposal loop.

A repo is correctly-minimal (not a harness gap) when **all** of the following
are true:

1. It has no open issues / issue tracker usage.
2. No agent workflow (loop, CI skill run) targets it.
3. It is a config artifact, userscript, or thin support repo whose entire
   surface is a handful of committed files.

When in doubt: if a README and an issue tracker exist, the harness is wanted.

---

## Canonical harness-conformance baseline

Each item names the concern, the expected artifact/state, and the source that
requires it.

### A — `## Conventions` block in the instruction file

- **`CLAUDE.md`** (or `AGENTS.md`) contains a `## Conventions` heading with
  pointer sub-sections for: Issue tracker, Triage labels, Domain docs, Installed
  skills (where applicable), Skill editorial intent (skills repo only), and
  Intake convention (with a live Inbox issue URL).
  Source: `setup-dividedby-skills` SKILL.md Concern A; `CLAUDE.md` lines 11–52.

### B — Idea Inbox issue

- One GitHub issue labeled `idea-inbox` exists (open or closed), with a body
  whose first line is the hidden breadcrumb
  `<!-- agent-protocol: drain=docs/agents/idea-inbox.md -->`, followed by
  `## Ideas` and `## ✅ Actioned` headers.
  Source: `setup-dividedby-skills` SKILL.md Concern B.

### C — CORE label set on GitHub

- The following labels exist on the repo with canonical colors and descriptions,
  matching `docs/agents/labels.md`:
  - State: `needs-triage`, `ready-for-agent`, `ready-for-human`, `blocked`,
    `wontfix`, `idea-inbox`
  - Category: `bug`, `enhancement`, `chore`, `epic`
  - Size: `size:S`, `size:M`, `size:L`, `size:XL`
- `needs-info` is **absent** (Matt's setup installs it; the dividedby composed
  layer removes it).
- Stock labels (`documentation`, `duplicate`, `good first issue`, `help wanted`,
  `invalid`, `question`) are **absent**.
  Source: `setup-dividedby-skills` SKILL.md Concern C; `docs/agents/labels.md`.

### D — `docs/agents/triage-labels.md` (dividedby content)

- The file exists and contains the dividedby CORE/LOOP-NETWORK/CHANNELS tiering
  structure (not Matt's version). It is seeded from `docs/agents/labels.md` with
  repo-specific references adapted.
- `needs-info` does not appear in any CORE section of this file.
- Any `docs/agents/*.md` files that previously referenced `needs-info` or
  Matt-specific role→label wording have been reconciled to the dividedby
  convention.
  Source: `setup-dividedby-skills` SKILL.md Concern D.

### E — `docs/agents/idea-inbox.md`

- The file exists and contains the drain protocol (the breadcrumb discovery
  path, capture rules, drain steps, rolling-window rule). It is the pointer
  target for the Intake convention in the `## Conventions` block.
  Source: `setup-dividedby-skills` SKILL.md Concern E; `docs/agents/idea-inbox.md`.

### F — Branching/merge policy

- The repo is listed in `~/.claude/branching-flow.md` under its correct tier
  (library/tool or deployed app).
- GitHub merge settings match the universal mechanics:
  `allow_squash_merge=false`, `allow_rebase_merge=false`,
  `allow_merge_commit=true`, `delete_branch_on_merge=true`.
- Default branch matches the repo's role classification.
  Source: `setup-dividedby-skills` SKILL.md Concern F.

### G — Claude harness (`.claude/settings.json` + hooks)

- `.claude/settings.json` exists with the deny-only permissions model and the
  hook entries expected by `project-claude-config`.
- The five standard PreToolUse hooks are wired (read-guard, bash-guard,
  git-guard, secret-guard, typecheck-guard) per the `project-claude-config`
  catalog.
  Source: `project-claude-config` SKILL.md; ADR 0023 (project-claude-config owns
  the harness; setup-dividedby-skills explicitly excludes it).

### H — Domain surface

- `CONTEXT.md` exists at the repo root with the repo's vocabulary glossary.
- `docs/adr/` exists (even if initially empty) for architectural decisions.
  Source: `docs/agents/domain.md`; `setup-dividedby-skills` Step 1 detects
  these artifacts as pre-existing; `setup-matt-pocock-skills` Step 2 Section C
  confirms/records the layout (single-context vs multi-context) but does not
  itself create `CONTEXT.md` or `docs/adr/`. Which skill or manual step
  *creates* these files on a greenfield repo is unconfirmed — treat as a
  prerequisite the operator is expected to supply before running either setup
  skill.

### I — `docs/agents/issue-tracker.md` and `docs/agents/domain.md`

- Both pointer docs exist, providing the `gh` CLI conventions and domain-doc
  discovery rules respectively. They are expected in the target by the
  `## Conventions` block's pointers.
  Source: `docs/agents/issue-tracker.md`; `docs/agents/domain.md`; referenced
  from `CLAUDE.md` Conventions block pointer lines.

---

## Four-bucket definitions

Buckets are mutually exclusive. Assign a repo to the **first** bucket whose
criteria it satisfies, in the order below.

### 1. Correctly-minimal

Meets the applicability bar for "no harness wanted":
- No issue-tracker usage, no agent workflow, thin config/support repo.

A correctly-minimal repo has no harness gap by definition. No remediation.

### 2. Missing-but-wanted

Fails the applicability bar test (harness is warranted) **and** zero or near-zero
harness elements are present — the repo has never been onboarded.

Remediation: run `project-claude-config` then `setup-dividedby-skills` in full.

### 3. Orphan-scaffold

One or more harness elements exist but the setup was never completed — partial
state with no coherent baseline. Typically: a `docs/agents/` dir exists but
labels are stock, or a `## Conventions` block points at non-existent files.

Mutually exclusive from "drifted" because there is no coherent prior baseline
to drift from — it was never in sync.

Remediation: run `setup-dividedby-skills` (it is idempotent; skip = dominant
outcome on already-correct items).

### 4. Drifted

Was fully onboarded (all baseline items were once present and correct), but
one or more items have since diverged: label colors changed, `needs-info`
re-appeared, `triage-labels.md` reverted to Matt's version, merge settings
were overridden, etc.

Mutually exclusive from "orphan-scaffold" because it had a coherent baseline.
Evidence of prior full setup (e.g. correct Inbox issue, correct label set at
some point in git/issue history) is the distinguishing signal.

Remediation: targeted `setup-dividedby-skills` re-run; skip-dominant pass will
identify and fix only the drifted items.

---

## Two-axis note

The divergence scan operates on **two independent axes that must not be
conflated**:

**Axis 1 — Harness drift** (applies to ALL dividedby repos)
Measured against this baseline. The scan checks whether each repo's
harness elements match the current output of `setup-dividedby-skills`. The
lever to fix drift is `setup-dividedby-skills` (re-run, idempotent).

**Axis 2 — Skills-vs-upstream divergence** (applies to the SKILLS REPO ONLY)
Measured against `mattpocock/skills` upstream. The lever is
`skill-divergence-audit` (a separate skill). This axis asks "have our published
skills drifted from Matt's revamped foundation?" — that is a different question
from "does this repo carry the harness?" and is only meaningful for
`dividedby/skills` itself.

Conflating the axes produces false positives: a Consumer repo can be perfectly
harness-conformant while also being out of scope for skills-vs-upstream analysis.
Treat each axis as its own scan pass with its own output bucket.

---

## Note on test coverage

`skills/config/setup-dividedby-skills/labels.test.py` guards the canonical
label registry (Baseline item C + D) against accidental mutation of the
CORE/LOOP split and the `needs-info` suppression posture. No equivalent test
guards this baseline doc itself — whether one is warranted (e.g. a test that
asserts all nine baseline items are present in this file by heading) is a
judgment call for the lead. Flagging rather than building it here.
