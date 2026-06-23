# Cross-repo credential is selected inside cli.py, not the workflow shell

## Context

The `apply-agent-research` reusable body was hardened in #394 (ADR 0029): scoped
`--allowedTools`, SHA-pinned checkout, no bare `Bash(...:*)`, no `--permission-mode
acceptEdits`. The scoped allowlist permits `python3 "$SKILL_DIR/lib/cli.py" …` shapes
but denies arbitrary shell env-prefix patterns like
`GH_TOKEN="$SKILLS_TRACKER_TOKEN" gh …`. That env-prefix was exactly how consumer
repos performed the `GITHUB_TOKEN` → `SKILLS_TRACKER_TOKEN` swap for every
cross-repo `gh` call into `dividedby/skills` — so the #394 hardening silently
no-opped consumer `skill-request` and `skill-promotion` filing (#418).

Three shapes of the regression were present in the prompt:

1. The open-issues **list** (dedup read): bare `GH_TOKEN="$…" gh issue list --repo
   dividedby/skills`.
2. The **file** write: `cli.py file` was already routed through the shim, but the
   prompt instructed the agent to prepend `GH_TOKEN="$SKILLS_TRACKER_TOKEN"` before
   calling it — which the allowlist blocks.
3. The **+1 comment** write: same pattern.

The root cause is that token selection lived in the prompt/shell layer rather than
inside the one allowlisted path (`cli.py`).

## Decision

Move token selection into `cli.py` itself.

- A module constant `CROSS_REPO = "dividedby/skills"` and a helper `_gh_env(repo)`
  read `SKILLS_TRACKER_TOKEN` from the cli.py process environment and inject it as
  `GH_TOKEN` in the `subprocess.run` env **only** when `repo == CROSS_REPO`. Any
  other `--repo` value (or absent `--repo`) keeps the ambient credential unchanged.
- `_file`, `_comment`, and the new `_find_open` handler each pass `env=_gh_env(args.repo)`.
- A new subcommand `find-open --repo <r> --label <l> --capability <slug>` replaces
  the bare `gh issue list` dedup read: it lists open issues by label, prints the
  first issue number whose body contains `<!-- capability: <slug> -->`, or prints
  nothing on no match (exit 0). A `gh` failure exits non-zero and passes stderr
  through — it must never collapse into the silent "no match" signal, which would
  cause a duplicate file instead of a `+1`.
- The harness prompt (`harness/prompts/apply-agent-research.md`) is updated to use
  `find-open` for all dedup reads, and to remove every `GH_TOKEN=` instruction.
  Zero `GH_TOKEN=` occurrences remain in the prompt.

The fix ships via the fresh-clone pattern (ADR 0014): every run clones
`dividedby/skills` fresh and invokes `cli.py` from the clone, so updated cli.py
logic reaches all consumers on their next scheduled run without any tag move and
without touching `.github/workflows/apply-agent-research-reusable.yml`.

## Security invariant

`SKILLS_TRACKER_TOKEN` is injected into a `gh` subprocess env **only** when the
`--repo` argument is exactly the string `"dividedby/skills"`. Any other repo string
— including a Consumer's own repo — receives the ambient credential. This limits
the blast radius of a prompt-injection that attempts to exfiltrate the PAT by
specifying a different `--repo`: the swap simply does not occur.

## Consequences

- Consumers no longer set `GH_TOKEN` in the shell for any cross-repo call.
- All three `dividedby/skills` operations (`find-open`, `file`, `comment`) are now
  allowlist-safe: they all resolve to `python3 "$SKILL_DIR/lib/cli.py" …`.
- `find-open` is the authoritative cross-repo dedup read; direct `gh issue list
  --repo dividedby/skills` is no longer needed in the prompt or skill guidance.
- The design docs (`docs/design/skill-request-flow.md`,
  `docs/design/skill-promotion-flow.md`) are updated to document the new invariant.

## References

- [ADR 0029](0029-apply-agent-research-joins-the-reusable-body-rail.md) — the rail fold that introduced the scoped allowlist
- [ADR 0014](0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md) — fetch-fresh pattern; why no tag move is needed
- [ADR 0015](0015-apply-agent-research-prompt-is-consumer-portable-via-env.md) — env-wiring portability; SKILLS_TRACKER_TOKEN as the role discriminator
- Issue #418 — regression report
- Issue #394 — the hardening PR that introduced the scoped allowlist
