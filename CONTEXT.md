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

**Supporting file**:
A markdown file inside a skill folder that the `SKILL.md` links to for
detail (e.g. `banned-patterns.md`, `direction-doc-format.md`).
_Avoid_: doc, reference, attachment.

**Run-book**:
A cron-driven prompt that an unattended ("AFK") agent follows to perform a
recurring workflow. Lives in the repo but is **not** a published skill — it
orchestrates, and may invoke skills as steps. The self-improvement and
gap-scanner workflows are run-books, not skills.
_Avoid_: skill, script, job, automation.

**Integration map**:
A standing analysis doc, auto-maintained by the self-improvement run-book,
that maps the skills in this repo to the external practices/artifacts tracked
in the `agent-research` knowledge base. Used as the diff baseline that surfaces
refinement opportunities. Lives consumer-side (here), never in `agent-research`.
_Avoid_: crosswalk, comparison table, matrix.
