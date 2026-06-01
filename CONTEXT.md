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

**Supporting file**:
A markdown file inside a skill folder that the `SKILL.md` links to for
detail (e.g. `banned-patterns.md`, `direction-doc-format.md`).
_Avoid_: doc, reference, attachment.

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
