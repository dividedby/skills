# Consolidate write tokens into ISSUES_TOKEN and make host/consumer mode an explicit flag

## Context

Three distinct write PATs served the cross-repo fleet:

1. **`SKILLS_TRACKER_TOKEN`** — Issues:RW on `dividedby/skills` only; held per consumer
   repo; the cross-repo credential for `skill-request`/`skill-promotion` filing.
2. **`DRIFT_CHECK_TOKEN`** — Contents:read on active consumer repos; held by
   `dividedby/skills`; used by the drift detectors (`check-workflow-drift`,
   `check-label-drift`).
3. An unused "agent-research" write PAT — never wired into production.

ADR 0031 ratified these as per-role least-privilege PATs. Issue #424 audited the
estate and raised the consolidation question: three token identities vs one.

A second design pressure emerged from the consolidation itself: the host/consumer
mode discriminator in `cli.py mode` was **token presence** (ADR 0015, updated ADR
0030). Because `dividedby/skills` now holds `ISSUES_TOKEN` for the drift detectors,
the old discriminator would incorrectly classify the skills host as a consumer.
Mode must become an explicit signal independent of token presence.

## Decision

### (a) Token consolidation

Replace all three write-PAT identities with one **`ISSUES_TOKEN`**: a fine-grained
PAT scoped to **all repositories** (current and future) with **Issues:RW +
Contents:read** permissions. This overrides ADR 0031's "keep write tokens scoped"
stance for the tracker-write and drift-read roles.

| Old token | New token | Where held | Disposition |
|---|---|---|---|
| `SKILLS_TRACKER_TOKEN` | `ISSUES_TOKEN` | each consumer repo | migrate; old name accepted as Option-B fallback |
| `DRIFT_CHECK_TOKEN` | `ISSUES_TOKEN` | `dividedby/skills` | migrate; old name accepted as Option-B fallback |
| agent-research write PAT | — | — | revoke without migration (never wired) |

**Option-B fallback (non-breaking transition):** workflow env lines use
`${{ secrets.ISSUES_TOKEN || secrets.DRIFT_CHECK_TOKEN }}` and
`${{ secrets.ISSUES_TOKEN || secrets.SKILLS_TRACKER_TOKEN }}` so existing secrets
keep working until repos are updated. Both old secret declarations remain in the
reusable-body `secrets:` block during the transition window.

### (b) Explicit mode flag

Replace the token-presence discriminator with an explicit `is-tracker-host` boolean
`workflow_call` input on `apply-agent-research-reusable.yml` (default `false`).

The reusable body exports `IS_TRACKER_HOST: ${{ inputs.is-tracker-host }}` into the
job env. `cli.py mode` reads `IS_TRACKER_HOST`: the string `"true"` (case-insensitive)
prints `host`; any other value (including unset or `"false"`) prints `consumer`.
Default is `consumer` so a misconfigured workflow fails safe rather than draining
into the wrong tracker.

The `dividedby/skills` host caller sets `is-tracker-host: true` in its stub.
Consumer callers omit the input (default `false`).

### (c) The `repo == dividedby/skills` swap guard is retained

`_gh_env` in `cli.py` injects `ISSUES_TOKEN` as `GH_TOKEN` **only** when
`--repo == "dividedby/skills"`. This guard (ADR 0030) becomes *more* important now:
`ISSUES_TOKEN` is scoped to all repositories, so a prompt-injection that substitutes
a different `--repo` would otherwise redirect the PAT to an arbitrary repo. The guard
bounds the blast radius to `dividedby/skills` regardless of the wider token scope.

## Security invariant

- `ISSUES_TOKEN` is injected into a subprocess env only when `--repo` is exactly
  `"dividedby/skills"`. Any other `--repo` receives the ambient credential.
- The token value is never printed, never set in `GH_TOKEN` by the caller workflow,
  and never read by the agent. cli.py owns all token selection.
- Mode (`host`/`consumer`) is set at the workflow input layer; neither the agent nor
  cli.py can escalate from consumer to host by manipulating env variables that
  the sandbox would deny anyway.

## Consequences

- **One token to provision and rotate.** Consumers provision `ISSUES_TOKEN` and
  `dividedby/skills` replaces `DRIFT_CHECK_TOKEN` with `ISSUES_TOKEN`. One PAT
  rotation covers both roles.
- **Wider blast radius accepted.** A leaked `ISSUES_TOKEN` can file issues on any
  repo and read contents of any repo (vs. `dividedby/skills`-only for tracker-write,
  consumer-repos-only for drift-read). The `repo == dividedby/skills` guard in
  cli.py bounds the token's *effective* use in the automated loop to that one repo.
  The maintainer accepts this trade for operational simplicity.
- **No unattended run is broken.** The Option-B fallback keeps existing secrets
  functional until the maintainer installs `ISSUES_TOKEN`. Consumer stubs with
  `SKILLS_TRACKER_TOKEN` continue to work.
- **ADR 0015's presence-discriminator is retired.** The host/consumer split is now
  encoded in the workflow stub (`is-tracker-host: true`), not inferred from whether
  the token env var is set. This eliminates the now-impossible invariant that "the
  host never holds the cross-repo PAT."
- **The `repo == dividedby/skills` guard (ADR 0030) is preserved.** Its importance
  increases with the wider token scope.

## References

- Issue #424 — consolidation spike and audit
- [ADR 0015](0015-apply-agent-research-prompt-is-consumer-portable-via-env.md) — env-wiring portability; superseded on the role-discriminator point
- [ADR 0030](0030-cross-repo-credential-selected-inside-cli-py.md) — token selection inside cli.py; the swap guard is retained
- [ADR 0031](0031-cross-repo-actions-tokens-are-per-role-fine-grained-pats.md) — per-role fine-grained PATs; superseded on tracker-write and drift-read scope
