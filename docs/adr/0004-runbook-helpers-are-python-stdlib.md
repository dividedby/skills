# Run-book decision helpers are Python stdlib, under `runbooks/`

> **Amendment (2026-06-01) — helpers relocated; `runbooks/` retired.** The
> decentralized-pull redesign (agent-research ADR 0019,
> [`cross-repo-knowledge-application`](../design/cross-repo-knowledge-application.md))
> moved consumption into the published `apply-agent-research` skill that each
> Consumer runs on *itself*. The skill enforces the leak guard and one-proposal
> cap mechanically, so it must invoke the gate/sanitizer CLI **wherever it is
> installed** — a path `runbooks/` (present only in this repo) cannot satisfy. The
> two surviving helpers + the `cli.py` seam therefore now live **under the skill**
> at `skills/meta/apply-agent-research/lib/`, invoked by file path
> (`python3 <skill-dir>/lib/cli.py …`, not `-m`, since the skill folder name is
> not an importable module), so they travel with the installed skill.
>
> This reverses the "Not skills" / "bundling … is ceremony" stance below, because
> the force that justified it is gone: the helpers were "internal machinery on the
> maintainer's runner," but they are now **runtime dependencies of a published
> skill that ships to other repos**. The rejected alternative was *a skill per
> helper* (ceremony, and it would publish machinery as a capability); co-locating
> two support files under the one skill that needs them is neither. Everything
> else holds unchanged: still stdlib-only, still pure (inputs in, decision out),
> still never registered in `plugin.json`. The original record stands below.

---

The skill-improvement run-books ([ADR 0003](./0003-skill-improvement-workflows-propose-via-issues.md))
lean on two **pure decision helpers**: a proposal gate (the ≤1-issue-per-run cap
plus dedup) and a sanitizer guard (blocks private-repo content from this public
tracker). The issues that specify them ([#15](https://github.com/dividedby/skills/issues/15),
[#18](https://github.com/dividedby/skills/issues/18)) require the cap and the
no-private-code rule to be enforced *mechanically, not by prompt discipline* —
the decision must not depend on model judgment. That makes them executable code,
not prose the agent re-derives each run. This is the repo's first application
code.

**Python 3, standard library only.** No `pyproject.toml`, no virtualenv, no
lockfile — just `.py` files, tested with stdlib `unittest`
(`python3 -m unittest discover -s runbooks`). This matches the maintainer's only
other code (the global Claude hooks, also stdlib Python) and keeps the repo
materially "markdown plus a few scripts." Node was rejected: the only Node in the
repo is the `npm install` that pulls in Claude Code itself
(`.github/workflows/improve-codebase-architecture.yml`), and idiomatic Node drags
in `package.json` + lockfile + `node_modules` — a second runtime and a heavier
footprint for two small functions.

**The purity boundary is load-bearing.** The helpers are pure: inputs in,
decision out. All tracker, git, and clone I/O lives in the run-books and is
injected. The gate takes candidate dicts and already-extracted open-issue dedup
keys; the sanitizer takes a body string and known private markers. Neither
touches transport, so the safety-critical logic is unit-testable without the live
tracker. The run-book invokes a helper as a deterministic step
(`python3 runbooks/lib/<helper>.py`, JSON in / decision out) and acts on the
result — prose orchestration around a code-enforced gate.

**Not skills.** These helpers live under `runbooks/`, never in `skills/` or
`plugin.json`. [ADR 0002](./0002-design-skills-prescribe-at-principle-level.md)
("code in a skill is illustrative, not literal") governs *published skills* and
does not bar this: a run-book helper is internal machinery, not a principle
taught to installers.

**Rejected alternatives.** A documented decision-spec the agent follows
(reintroduces the exact model judgment #15/#18 exist to remove; for a leak
sanitizer feeding a public tracker, a soft gate is a footgun). Bundling each
helper inside a tiny skill (keeps "skills are the only way to add capability,"
but is ceremony out of proportion to two pure functions, and would publish
internal machinery). pytest (nicer parametrized tables, but a third-party dep
and lockfile defeat the zero-footprint goal; revisit only if the helper suite
grows well past two functions).
