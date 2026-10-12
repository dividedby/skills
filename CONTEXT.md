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
Currently `engineering/` and `config/`.
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
([ADR 0023](./docs/adr/0023-setup-dividedby-skills-vs-project-claude-config-seam.md);
that skill has since been retired).
_Avoid_: false all-clear, clean report, whole-repo green.

**Guard hook**:
A deterministic PreToolUse hook that blocks a class of dangerous commands by
exiting non-zero (e.g. `bash-guard.py`, `pnpm-guard`, a git-guard). The
**deterministic** counterpart to a **Convention** (a prose rule): a convention
only lowers the odds an agent does the harmful thing, a guard hook makes it
impossible. Proposed/audited via the `config/` skill's (`project-claude-config`) `CATALOG.md`, not
as a standalone skill. A project-scope guard may re-declare a global one when the
run lacks global config (CI/AFK) — see
[ADR 0013](./docs/adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md).
Output convention: silent on pass (no output, exit 0); on a block, emit to stderr exactly the diagnostic the agent needs to correct course — no more — and exit non-zero.
_Avoid_: safety hook, blocker, validator.

**Supporting file**:
A markdown file inside a skill folder that the `SKILL.md` links to for
detail (e.g. `banned-patterns.md`, `direction-doc-format.md`).
_Avoid_: doc, reference, attachment.

**Idea Inbox**:
The single per-repo GitHub issue that is the canonical intake for **freeform,
unstructured** ideas — raw, unscoped thoughts. Items enter
**enriched** — the idea plus the ambient context/links available at file time, but
not yet grilled or scoped — and leave by **draining**: an adaptive promotion that
picks only the pipeline steps a given idea needs (`/grill-with-docs`, `/to-spec`,
`/to-tickets`, `/software-design`) and strives to emit a `ready-for-agent` issue
(strong agent brief, HITL steps folded in where needed), moving the item to a
`✅ Actioned` section with `→ #num`. **Structured, contract-bearing**
filings (e.g. a fully-scoped bug) **bypass the Inbox**
and file labeled issues directly. The unifying invariant is that every filing
becomes a tracked GitHub issue — not that every filing funnels through the Inbox.
_Avoid_: backlog, triage queue, scratchpad, inbox issue.


**Autonomous loop** (a.k.a. AFK loop):
An unattended agent run that repeats a work cycle until a stop condition,
guarded by a per-iteration feedback gate and an iteration/cost cap. The general
category over a **Proposal loop** (its propose-only instance — never applies,
[ADR 0003](./docs/adr/0003-skill-improvement-workflows-propose-via-issues.md))
and an **applying loop** (commits or opens PRs on a green gate); a **Run-book**
is the scheduled wrapper around one. Setup methodology lives in the
`autonomous-loop` skill, which defers execution to an existing runtime rather
than reimplementing one.
_Avoid_: bot, daemon, automation, AFK bot.

**Run-book**:
A cron-driven prompt that an unattended ("AFK") agent follows to perform a
recurring workflow. Lives in the repo but is **not itself** a published skill —
it orchestrates, and may invoke skills as steps, including as a thin scheduled
wrapper around a single published skill. The reusable *capability* it invokes
can be a published skill; the run-book is only the schedule and the per-repo
wiring around it.
_Avoid_: skill, script, job, automation.

**In-session sub-agent**:
A sub-agent dispatched via the Agent tool **inside the live Claude Code
process** — subscription-covered, no new process. The mechanism a loop or
firewall reaches for **when a session already exists** (interactive or `/loop`):
it supplies the per-item context boundary the persistent session doesn't give for
free. Preferred over a **Headless process** whenever a session is available; the
fallback only fits where none is. Distinct from the `/loop`/`/schedule`/CI-cron
*runtime selection* ([ADR 0012](./docs/adr/0012-autonomous-loop-and-context-firewall-are-two-composing-skills.md)) — this is *how* a work item runs, not *which runtime* schedules it.
_Avoid_: child process, claude -p, Task, headless agent.

**Headless process**:
A fresh `claude -p` / Agent SDK process spawned with **no interactive session** —
the mechanism for environments that have none (CI, cron, runners), where each
invocation is its own context boundary (a firewall per run) for free. The
**fallback when there is no session**, never the default inside one — an agent
running in the Claude Code CLI is *in* a session and should use an
**In-session sub-agent** instead. Reserving it for the no-session case also
avoids drawing on the Agent SDK credit (see #58) — but that cost is secondary;
the routing is environment-fit first.
_Avoid_: headless runtime, batch agent, claude -p (generically), detached runtime.

**Proposal loop**:
The propose-only instance of an **Autonomous loop**: an unattended,
skill-driven run that reads an input, then **proposes via labeled issues and
never applies** — no commits, edits, or PRs (the producer/decider split,
[ADR 0003](./docs/adr/0003-skill-improvement-workflows-propose-via-issues.md)).
This repo no longer runs any scheduled proposal loops
([ADR 0039](./docs/adr/0039-retire-remaining-proposal-loops-and-loop-serving-skills.md));
the term survives as the strictest point on the `autonomous-loop` gate spectrum.
_Avoid_: bot, pipeline, automation.

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
