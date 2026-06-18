---
name: doc-it
description: >
  Scan a repo and generate or patch its reference documentation (README, API
  docs, onboarding guide, CHANGELOG) from source — applying changes directly.
  Audits existing ADRs and CONTEXT.md for staleness and drift, but reports
  findings only; never edits decision records. Use when reference docs are
  missing, stale, or out of sync with the code.
---

# Doc-It

This skill scans a repo and brings its **reference documentation** — the
README, API docs, onboarding guide, and CHANGELOG — into sync with the source.

Two postures, fixed:

- **Apply** — generate missing reference docs, patch stale ones.
- **Report-only** — surface ADR / `CONTEXT.md` staleness findings; never
  mutate them.

## Spine

**scan → audit → draft → apply → render**

### Scan — read the repo, don't assume

Walk the local repo. Read the source (modules, exports, entry points, config
files) and the existing docs side-by-side. No network — all inputs are local
repo files. Record:

- Which reference doc types exist and where.
- Which are **missing** entirely.
- Which exist but are **stale** — contents don't match what the source
  currently exports, requires, or describes.
- Which ADRs or `CONTEXT.md` terms appear to have drifted against the code
  (renamed modules, removed concepts, changed APIs).

A reference doc is stale when a meaningful fact it states — a command, an API
signature, a file path, a concept name — is contradicted by what the source
actually does now. Surface-level wording differences are not staleness.

### Audit — classify the ADR / CONTEXT.md findings (report-only)

For each ADR and `CONTEXT.md` term that the scan flagged, produce a one-line
finding: what drifted and what the current source says. This list is the
complete output for decision records — the skill stops there. It does **not**
edit ADRs, add or remove `CONTEXT.md` terms, or author new decisions.

*What good looks like:*

> ADR 0007 — references `auth-service`; module was renamed to
> `identity-service` in commit abc1234. CONTEXT.md term `pipeline` —
> describes a push-based flow; code now uses polling.

Two or three precise, actionable lines are the target. Not a narrative.

### Draft — generate or patch reference docs

For each reference doc type that is missing or stale, draft the replacement or
patch. Draft from the source — read the code and config, not the old doc.

**README** — orient a new reader: what the project does, how to install or
run it, the top-level entry points, and a pointer to the relevant ADRs for
decisions that shaped the design. Do not restate the decisions; link to them.

**API docs** — one entry per exported public surface: name, signature or
shape, what it does, what it accepts and returns, failure modes. Keep
language-agnostic at the principle level; the exact idiom (docstring, JSDoc,
OpenAPI fragment) is determined by what the repo already uses.

**Onboarding guide** — the fastest path from a clean checkout to a working
change: environment prerequisites, setup steps, how to run tests, and where
the key concepts live. Derive the steps from the actual repo layout and
scripts, not from a generic template.

**CHANGELOG** — a human-readable log of what changed and when, grouped by
release or date. Derive entries from commit history and merged PRs (local
`git log`). Record facts; do not editorialize. If the repo has an existing
CHANGELOG format, match it exactly.

One principle holds across all four types: **link to existing ADRs for
decisions, do not restate or invent them.** If a design choice is documented
in an ADR, the reference doc points there rather than paraphrasing the
rationale. A reference doc that duplicates a decision record will drift from it.

### Apply — write the reference docs

Apply the drafts. For **missing** docs: create the file. For **stale** docs:
patch only the stale sections — preserve surrounding content and formatting
conventions the project already uses. Do not reformat a doc wholesale because
a section needed updating.

Never apply to:

- ADRs or `CONTEXT.md` — decision records are load-bearing; auto-edits risk
  corrupting the rationale. Audit findings only (above).
- Claude-config files (`CLAUDE.md`, `.claude/settings.json`, hooks) — deferred
  to `project-claude-config`.
- Files outside the local repo.

### Render — one structured output

Emit a single structured summary:

- **Applied** — each file created or patched, with one line on what changed.
- **ADR / CONTEXT.md findings** — the list from the audit station, unchanged.
  Label it clearly as report-only; a human decides what to do with each item.
- **Deferred** — anything the skill explicitly does not touch and why.

## Scope and boundaries

**This skill improves what exists; it does not author what is new.**

- **Defers new-decision authorship** to `grill-with-docs`. If a doc gap turns
  out to need a new architectural decision (not just a missing fact), surface
  it as an open question and stop — don't invent the decision. See
  [ADR 0022](../../../docs/adr/0022-doc-it-vs-grill-with-docs-authoring-auditing-boundary.md)
  for the clean seam between these two skills.
- **Defers Claude-config docs** to `project-claude-config`.
- **No network.** The scan surface is local repo files only. Deterministic;
  AFK-safe.
- **No template library.** At most one inline sketch per doc type (see the
  Draft station). A template library and a high/low-signal example library are
  out of scope (named follow-up in issue #288).
- **Used as a delegate from `repo-audit`** when a full doc pass is warranted.
