# Project-scope hooks may re-declare a global guard when the run lacks global config

Both harness skills (`init-project-harness`, `audit-project-harness`) open by
reading `~/.claude/settings.json`, treating the global guards (`bash-guard.py`,
`read-guard.py`) as **already in effect**, and refuse to re-declare a global hook
because hooks are **additive across scopes** — a re-declared global hook fires
twice. This ADR carves out one exception: a project-scope hook **may** re-declare
a global guard when the run context does not carry the global config — i.e. an
AFK/CI run of `claude -p` where `~/.claude/` is absent.

**Why.** The no-re-declare rule rests on an unstated assumption: that the global
harness *travels with every run*. It doesn't. A Consumer running
`apply-agent-research` under `claude -p` in CI (the motivating case, #74, for
[goodreads-bot#54]) has no `~/.claude/` — the maintainer's `bash-guard.py` git
protections simply aren't there. In that context a prose rule ("never
`push --force`") only lowers the odds of harm; only a project-registered
PreToolUse hook (exit 2) makes the destructive command impossible. Re-declaring
at project scope is therefore not duplication — it is the *only* copy that runs.
This is the deterministic guard named as guardrail (1) of the HITL→AFK graduation
in [ADR 0012](./0012-autonomous-loop-and-context-firewall-are-two-composing-skills.md),
where "the #64 git-guard" is the worked example for hardening an unattended loop.

**The trigger is run-context, not repo-state.** The existing catalog triggers
(formatter present, secret files present) are repo-state facts an Explore pass
detects directly. "Will this repo run agents where the global guard is absent?"
is a deployment/intent fact. The harness skills detect it by proxy: a CI workflow
that invokes `claude -p` / an agent runner, or an existing project-scope guard
hook (goodreads-bot's `pnpm-guard` is the tell). When that proxy fires, the
double-fire concern is moot — on a developer's machine the global guard makes the
project copy redundant-but-harmless; in CI the project copy is the sole guard.

**Catalog entry, not a new skill.** The git-guardrails capability requested in
#74 ships as a `CATALOG.md` entry consumed by the existing harness skills, plus a
shared Step-1 principle stating this carve-out — **not** a standalone published
skill. The install/audit verbs it needs (`init-project-harness` proposes,
`audit-project-harness`'s `add` recommends) already exist; a new skill would
re-implement them. This call is reversible and follows the repo's improve-existing
bias ([ADR 0001](./0001-buckets-cluster-by-user-intent.md) discourages
single-purpose proliferation), so it is recorded here only as context, not as the
decision under trade-off.

**Rejected alternatives.** *Keep the absolute no-re-declare rule* — leaves CI/AFK
runs with zero git protection, defeating the guardrail that makes unattended
applying loops safe. *Detect global-absence at hook runtime instead of proposing
unconditionally* — the hook can't reliably introspect whether a global twin will
also fire, and a doubly-firing exit-2 guard is harmless (same block, one extra
log line), so gating on a cheap repo-side proxy is simpler and safe. *Narrow the
carve-out to the git-guard catalog entry's "why" note only* — loses the reusable
principle; the same logic applies to any guard that must run where global config
is absent, so it belongs in both skills' Step 1.

[goodreads-bot#54]: https://github.com/dividedby/goodreads-bot/issues/54
