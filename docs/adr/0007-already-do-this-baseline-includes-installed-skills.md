# The already-do-this baseline includes the host's installed-skill inventory

[`apply-agent-research`](../../skills/meta/apply-agent-research/SKILL.md)'s
**already-do-this filter** asks "does this repo already do this?" before
proposing an improvement. Its baseline was the host repo's own governance docs
and `skills/` ([ADR 0003](./0003-skill-improvement-workflows-propose-via-issues.md)
dropped the integration map in favor of those docs). That baseline is **blind to
skills installed outside the repo** — in the maintainer's global `~/.claude/`
environment — so the loop can propose rebuilding a capability the maintainer
already has in every session. Issue #43 ("add a grill-with-docs skill") was this
miss: the skill is installed globally, just not a file here.

**Decision.** The already-do-this baseline includes an **inventory of the host's
installed external skills/plugins** when the host commits one (this repo:
[`docs/agents/installed-skills.md`](../agents/installed-skills.md)). An installed
capability is treated as *present, not absent*: the loop never proposes rebuilding
it. Where there is a gap, the proposal is an **integration or novel use** with the
repo's own skills. The skill stays host-agnostic — it reads whatever inventory the
host provides and hardcodes no specific upstream.

**Why a committed snapshot rather than runtime enumeration.** The loop runs
**remotely in CI**; it has no access to the maintainer's local `~/.claude/`, so it
cannot list the install at run time. A committed file is the only installed-skill
signal a remote run can read. The cost is that the snapshot is maintained by hand
and can drift — accepted, because the install set churns slowly and the file
carries its own refresh command.

**Rejected alternatives.**

- **Enumerate installed skills at run time.** Impossible for a remote CI run,
  which sees only what is committed. A local-only run could enumerate, but the
  loop must behave identically wherever it runs.
- **A literal install list in `CLAUDE.md`.** `CLAUDE.md` is instructions under an
  instruction budget; an inventory is reference data, not instruction. It belongs
  in `docs/agents/` alongside the other agent-facing reference docs, with a
  one-line pointer from `CLAUDE.md`.
- **Add the skills as files under this repo's `skills/` so the existing baseline
  sees them.** That is the rebuild #43 wrongly proposed — duplicating an installed
  external skill into this repo is the exact waste this decision prevents.
