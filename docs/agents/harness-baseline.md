# Harness Baseline

The canonical definition of a fully-onboarded `dividedby` repo, used by the
cross-repo divergence scan (epic #325) to classify every repo and drive
remediation. Every item traces to an actual output of the composed onboarding
skill set (`setup-dividedby-skills` plus the skills it composes on:
`setup-matt-pocock-skills` and `project-claude-config`), or to ADR 0024
(lean-on-upstream / soft-depend posture).

---

## Prerequisites

Supply these before running either setup skill on a greenfield repo. Neither
`setup-matt-pocock-skills` nor `setup-dividedby-skills` creates them — both
skills detect and record the layout they find.

- **`CONTEXT.md`** at the repo root — vocabulary glossary for the domain.
- **`docs/adr/`** directory — can be initially empty; the skills read from it.

Source: `setup-matt-pocock-skills` Step 1 (Explore) and Section C detect both
artifacts as pre-existing; `setup-dividedby-skills` Step 1 also detects them.

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

### Conventions block

- **`CLAUDE.md`** (or `AGENTS.md`) contains a `## Conventions` heading with
  pointer sub-sections for: Issue tracker, Triage labels, Domain docs, Installed
  skills (where applicable), Skill editorial intent (skills repo only), and
  Intake convention (with a live Inbox issue URL).
  Source: `setup-dividedby-skills` SKILL.md Concern A; `CLAUDE.md` lines 11–52.

### Idea Inbox issue

- One GitHub issue labeled `idea-inbox` exists (open or closed), with a body
  whose first line is the hidden breadcrumb
  `<!-- agent-protocol: drain=docs/agents/idea-inbox.md -->`, followed by
  `## Ideas` and `## ✅ Actioned` headers.
  Source: `setup-dividedby-skills` SKILL.md Concern B.

### GitHub label set

- The following labels exist on the repo with canonical colors and descriptions,
  matching `dividedby/skills docs/agents/labels.md` (authoritative source):
  - State: `needs-triage`, `ready-for-agent`, `ready-for-human`, `blocked`,
    `wontfix`, `idea-inbox`
  - Category: `bug`, `enhancement`, `chore`, `epic`
  - Size: `size:S`, `size:M`, `size:L`, `size:XL`
- `needs-info` is **absent** (Matt's setup installs it; the dividedby composed
  layer removes it).
- Stock labels (`documentation`, `duplicate`, `good first issue`, `help wanted`,
  `invalid`, `question`) are **absent**.
  Source: `setup-dividedby-skills` SKILL.md Concern C; `dividedby/skills docs/agents/labels.md`.

### Label convention doc (`docs/agents/triage-labels.md`)

- The file exists in the **onboarded repo** and contains the dividedby
  CORE/LOOP-NETWORK/CHANNELS tiering structure (not Matt's version).
- Background: `setup-matt-pocock-skills` creates `docs/agents/triage-labels.md`
  from its own template. `setup-dividedby-skills` Concern D then overwrites it
  with content seeded from `dividedby/skills docs/agents/labels.md`, adapted to
  the target repo. The filename `triage-labels.md` is Matt's convention; the
  content is dividedby's. The Conventions block pointer in the target must
  reference `docs/agents/triage-labels.md` — **not** `docs/agents/labels.md`
  (which does not exist in onboarded consumer repos).
- `needs-info` does not appear in any CORE section of this file.
- Any `docs/agents/*.md` files that previously referenced `needs-info` or
  Matt-specific role→label wording have been reconciled to the dividedby
  convention.
  Source: `setup-dividedby-skills` SKILL.md Concern D; `setup-matt-pocock-skills` Step 4.

### Idea Inbox doc (`docs/agents/idea-inbox.md`)

- The file exists and contains the drain protocol (the breadcrumb discovery
  path, capture rules, drain steps, rolling-window rule). It is the pointer
  target for the Intake convention in the `## Conventions` block.
  Source: `setup-dividedby-skills` SKILL.md Concern E; `docs/agents/idea-inbox.md`.

### Branching and merge policy

- The repo is listed in `~/.claude/branching-flow.md` under its correct tier
  (library/tool or deployed app).
- GitHub merge settings match the universal mechanics:
  `allow_squash_merge=false`, `allow_rebase_merge=false`,
  `allow_merge_commit=true`, `delete_branch_on_merge=true`.
- Default branch matches the repo's role classification.
  Source: `setup-dividedby-skills` SKILL.md Concern F.

### Claude harness (`.claude/settings.json`)

- `.claude/settings.json` exists (where the repo needs one) with the deny-only
  permissions model and any repo-specific `env`/permission entries
  `project-claude-config` prescribes.
- **The hooks are global, not per-repo.** The five PreToolUse guards (read-guard,
  bash-guard, git-guard, secret-guard, typecheck-guard) live in `~/.claude/` and
  are already in effect for every interactive session. A repo must **not**
  re-declare them at project scope — hooks are additive across scopes, so a
  re-declared global hook fires twice. Their absence from a repo's
  `.claude/settings.json` is **not** a gap.
- **CI/AFK carve-out (loop repos only):** a repo that runs headless `claude -p`
  in CI has no `~/.claude/`, so it re-declares the guard(s) that run needs at
  project scope — primarily `git-guard` — so they still fire unattended. For a
  loop repo, a *missing* project-scope `git-guard` is the real gap; for a
  non-loop repo, no project-scope hooks are expected at all.
  Source: ADR 0023 (project-claude-config owns the harness); ADR 0013 (project
  scope may re-declare a global guard for CI/AFK); `project-claude-config`
  SKILL.md / CATALOG.md.

### Pointer docs (`docs/agents/issue-tracker.md` and `docs/agents/domain.md`)

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

One or more harness elements exist but are unreferenced or unused by any active
workflow — partial state that was never completed. Detectable from present repo
state: harness files exist on disk (e.g. `docs/agents/`) but the Conventions
block is absent or points at missing files, labels are stock GitHub defaults, or
no Inbox issue carries `idea-inbox`.

Remediation: run `setup-dividedby-skills` (it is idempotent; skip = dominant
outcome on already-correct items).

### 4. Drifted

Harness elements are present **and in use by workflows**, but one or more have
diverged from the current baseline — label colors changed, `needs-info`
re-appeared, `triage-labels.md` reverted to Matt's version, merge settings were
overridden, etc. Detectable from present repo state: Conventions block points at
files that exist, Inbox issue is wired, but a live diff against the baseline
shows divergence.

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
skills drifted from Matt's revamped foundation?" — a different question from
"does this repo carry the harness?" and only meaningful for `dividedby/skills`
itself. The composed-skill relationship (this repo extends Matt's foundation
rather than replacing it) is grounded in ADR 0024.

Conflating the axes produces false positives: a Consumer repo can be perfectly
harness-conformant while also being out of scope for skills-vs-upstream analysis.
Treat each axis as its own scan pass with its own output bucket.
