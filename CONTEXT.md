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
Currently `engineering/`, `config/`, and `meta/`.
_Avoid_: category, namespace, group.

**Convention**:
A cross-cutting rule that multiple skills follow, documented under
`docs/agents/<name>.md` and referenced from `CLAUDE.md`. Not invokable —
read by skills during their work.
_Avoid_: agent skill, shared rule, policy.

**Guard hook**:
A deterministic PreToolUse hook that blocks a class of dangerous commands by
exiting non-zero (e.g. `bash-guard.py`, `pnpm-guard`, a git-guard). The
**deterministic** counterpart to a **Convention** (a prose rule): a convention
only lowers the odds an agent does the harmful thing, a guard hook makes it
impossible. Proposed/audited via the `config/` harness skills' `CATALOG.md`, not
as a standalone skill. A project-scope guard may re-declare a global one when the
run lacks global config (CI/AFK) — see
[ADR 0013](./docs/adr/0013-project-scope-hooks-may-redeclare-global-guards-for-ci.md).
_Avoid_: safety hook, blocker, validator.

**Supporting file**:
A markdown file inside a skill folder that the `SKILL.md` links to for
detail (e.g. `banned-patterns.md`, `direction-doc-format.md`).
_Avoid_: doc, reference, attachment.

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

**Knowledge mirror**:
A public, read-only repository holding a verbatim copy of `agent-research`'s
synthesized `knowledge/` tree — the credential-free read surface that consumers
clone. Derived from (never authoritative over) the private `agent-research`;
its raw `sources/` are never mirrored. Pushed by `agent-research`'s synthesize
workflow, commit-if-changed.
_Avoid_: cache, export, feed, snapshot.

**Consumer**:
A repo that runs the `apply-agent-research` loop on *itself* — reading the
knowledge mirror (or, if it is the knowledge source, its own `knowledge/`
tree) and proposing agent-meta improvements into its own tracker. In the
decentralized-pull model a Consumer depends on `dividedby/skills` one-way;
`agent-research` never depends on a Consumer. A Consumer fetches the skill
fresh at run time rather than committing a copy (see
[ADR 0008](./docs/adr/0008-consumers-fetch-the-skill-fresh-not-vendored.md)).
_Avoid_: subscriber, client, downstream repo.

**Proposal loop**:
The propose-only instance of an **Autonomous loop**: a scheduled, skill-driven
workflow that reads an input, then **proposes via labeled issues and never
applies** — no commits, edits, or PRs (the producer/decider split,
[ADR 0003](./docs/adr/0003-skill-improvement-workflows-propose-via-issues.md)).
It fetches its skill fresh each run rather than vendoring it
([ADR 0008](./docs/adr/0008-consumers-fetch-the-skill-fresh-not-vendored.md)).
`apply-agent-research` (KB → agent-meta) and `improve-codebase-architecture`
(codebase → refactors) are two members of this family, sharing one harness; the
shared shape is documented in
[`docs/onboarding/proposal-loop-harness.md`](./docs/onboarding/proposal-loop-harness.md).
_Avoid_: bot, pipeline, automation.

**Local skill**:
A skill that lives in a **Consumer**'s own repo, not published to
`dividedby/skills`. Invokable only within that Consumer. The **supply-side
audit** classifies each as *redundant* (duplicates a published or installed
skill — adopt the canonical one), *promotable* (novel and broadly useful — a
**promotion candidate**), or *repo-specific* (legitimately local — keep).
_Avoid_: private skill, custom skill, internal skill.

**Supply-side audit**:
The step in a Consumer's `apply-agent-research` loop that enumerates the
Consumer's **local skills** and matches each against the known skill universe
(the published `dividedby/skills` catalog + the installed-skill snapshot). It is
the **mirror of the demand-side already-do-this filter**
([ADR 0009](./docs/adr/0009-skill-request-checks-existing-and-installed-skills.md)):
0009 stops a Consumer *requesting* what already exists; the supply-side audit
inspects what the Consumer *already built*. See
[ADR 0010](./docs/adr/0010-consumers-audit-local-skills-supply-side.md).
_Avoid_: local-skill scan, dedup check.

**Skill promotion**:
A Consumer **offering a local skill up** to `dividedby/skills` for adoption as a
published skill — the **supply** twin of a **skill-request** (demand). Filed as
a `skill-promotion` issue with the same capability-key / `+1` / leak-guard
machinery as a skill-request but inverse semantics. See
[`docs/design/skill-promotion-flow.md`](./docs/design/skill-promotion-flow.md).
_Avoid_: skill donation, upstreaming, contribution.
