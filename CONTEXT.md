# dividedby-skills

A personal Claude Code plugin housing reusable skills. This glossary defines
the vocabulary of authoring skills in this repo. It is written for the
primary maintainer (Connor) and for agents working in this codebase — not
for external installers, who only see the published plugin.

## Language

**Skill**:
A folder under `skills/<bucket>/` containing a `SKILL.md` and any supporting
files. Invokable by Claude Code via its `name:` slug.
_Avoid_: command, tool, prompt.

**Bucket**:
A top-level grouping under `skills/` that clusters skills by use case.
Currently `engineering/`.
_Avoid_: category, namespace, group.

**Convention**:
A cross-cutting rule that multiple skills follow, documented under
`docs/agents/<name>.md` and referenced from `CLAUDE.md`. Not invokable —
read by skills during their work.
_Avoid_: agent skill, shared rule, policy.

**All-clear scope**:
The rule that a skill reports "all clear" **only for the surfaces it owns**. When
it observes drift in a surface another skill owns, it does not absorb the fix and
does not imply a whole-repo clearance — it **flags the drift and names the owning
skill** to hand off. Born from `project-claude-config` reporting "config is fine"
while a label doc owned by a different skill had drifted
([ADR 0023](./docs/adr/0023-setup-dividedby-skills-vs-project-claude-config-seam.md));
the skills that owned the seam have since been retired
([ADR 0039](./docs/adr/0039-retire-remaining-proposal-loops-and-loop-serving-skills.md),
[ADR 0040](./docs/adr/0040-retire-unused-catalog-skills-and-fold-flow-pr-into-branching-flow.md)).
_Avoid_: false all-clear, clean report, whole-repo green.

**Guard hook**:
A deterministic PreToolUse hook that blocks a class of dangerous commands by
exiting non-zero (e.g. `bash-guard.py`, `pnpm-guard`, a git-guard). The
**deterministic** counterpart to a **Convention** (a prose rule): a convention
only lowers the odds an agent does the harmful thing, a guard hook makes it
impossible. A project-scope guard may re-declare a global one when the
run lacks global config (CI/AFK) — see
[ADR 0013](./docs/adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md).
Output convention: silent on pass (no output, exit 0); on a block, emit to stderr exactly the diagnostic the agent needs to correct course — no more — and exit non-zero.
_Avoid_: safety hook, blocker, validator.

**Supporting file**:
A file inside a skill folder that the `SKILL.md` links to: usually markdown
for detail (e.g. repo-audit's `briefs.md`), occasionally an asset the skill
fills in (e.g. repo-audit's `template.html`).
_Avoid_: doc, reference, attachment.

**Idea Inbox**:
The single per-repo GitHub issue that is the canonical intake for **freeform,
unstructured** ideas — raw, unscoped thoughts. Items enter
**enriched** — the idea plus the ambient context/links available at file time, but
not yet grilled or scoped — and leave by **draining**: an adaptive promotion that
picks only the pipeline steps a given idea needs (`/grill-with-docs`, `/to-spec`,
`/to-tickets`) and strives to emit a `ready-for-agent` issue
(strong agent brief, HITL steps folded in where needed), moving the item to a
`✅ Actioned` section with `→ #num`. **Structured, contract-bearing**
filings (e.g. a fully-scoped bug) **bypass the Inbox**
and file labeled issues directly. The unifying invariant is that every filing
becomes a tracked GitHub issue — not that every filing funnels through the Inbox.
_Avoid_: backlog, triage queue, scratchpad, inbox issue.


**Rejection record**:
One structured file under `.out-of-scope/` per **explicitly-refused** capability,
stating why it was declined and the **bar to revisit** — the demonstrated gap that
would reopen the decision. The *already-refused* counterpart to an **ADR**: an ADR
records a decision made, a rejection record a decision made *not* to act. Agents read it
directly and never re-propose a capability whose bar-to-revisit is unmet; it is
the durable home for a `wontfix` rationale that
issue bodies only cross-reference.
_Avoid_: wontfix doc, rejected-skill note, out-of-scope file.

## Upstream soft-dependencies

This repo defers to two upstream catalogs for the capabilities listed below
rather than reinventing them — the default posture is delete-and-soft-depend per
[ADR 0024](./docs/adr/0024-lean-on-upstream-skills-soft-depend-over-reinvent.md),
which now names both. Soft-dependency means expected to be installed alongside
this plugin; nothing from either catalog is vendored here.

**From `mattpocock/skills`:**

**Workflow:** `grill-with-docs`, `to-spec` / `to-tickets` / `tdd`,
`improve-codebase-architecture`, `code-review`

Upstream skills that are not installed in the maintainer environment are
intentionally **not** listed, so we declare no contract on them until they are
(trimmed 2026-10-12; see the amendment in ADR 0024).

**From `anthropics/claude-plugins-official`:** `typescript-lsp`, `pyright-lsp` —
already installed in the maintainer's baseline.

**Authoring standard.** Every kept or reworked skill in this repo prescribes at the
principle level and stays lean, per [`CODING_STANDARDS.md`](./CODING_STANDARDS.md) and
[ADR 0002](./docs/adr/0002-design-skills-prescribe-at-principle-level.md).
