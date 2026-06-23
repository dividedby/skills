# Changelog

All notable changes to this project's two published surfaces — the skills catalog and the `harness/` Python — are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `apply-agent-research` cli.py: `find-open` subcommand for cross-repo dedup reads without a bare `gh` call (#418)
- Top-level CHANGELOG.md (#397)
- CODING_STANDARDS.md (#398)
- docs/agents/skill-authoring.md (#405)
- `project-claude-config`: detect situational sections and propose `<important if>` gating (#399)
- `project-claude-config`: detect label-doc drift and hand off to `setup-dividedby-skills` (#402)
- `setup-dividedby-skills`: add must-fix outcome + force-canonical mode for drifted label conventions (#393)
- proposal-loop reusable workflows: SHA-pin actions, drop acceptEdits, scope allowedTools; Dependabot for actions (#394)
- `apply-agent-research` folds onto the claude-loops-v1 reusable rail: one `workflow_call` body (`apply-agent-research-reusable.yml`) replaces all five full-copy envelopes; each repo vendors a thin caller stub; hardened (no acceptEdits, scoped allowedTools, SHA-pinned checkout); ADR 0029 (#417)

### Fixed

- Consumer cross-repo `skill-request`/`skill-promotion` filing silently no-opped under the hardened scoped `--allowedTools` introduced in #394: the `GH_TOKEN="$SKILLS_TRACKER_TOKEN" gh …` env-prefix was denied by the allowlist. cli.py now selects `SKILLS_TRACKER_TOKEN` itself for any `--repo dividedby/skills` call (`find-open`/`file`/`comment`) — no env-prefix, no token value in the shell, no tag move required (#418)
- Consumer-mode detection also broke under the scoped allowlist: the agent could not inspect `$SKILLS_TRACKER_TOKEN` via `printenv`, `env`, shell expansion, or `python3 -c` — all denied by the sandbox. Fixed via the allowlist-safe `cli.py mode` subcommand (prints `host` or `consumer`, never the token value) (#418)

## [2026-06-23]

### Added

- `workflow-authoring` run-book ported from agent-research (#379)
- Reusable `workflow_call` bodies for arch-review and staleness proposal loops (#383)
- Drift guard covering the remaining vendored workflow surface (#387)
- LOCAL label as an explicit fourth tier in the label vocabulary (#392)

### Changed

- Skills default to user-invoked; `disable-model-invocation: true` set across all SKILL.md files (#407)
- Intake convention gated behind `<important if>` in CLAUDE.md to reduce ambient context load (#396)
- Config-seam drift rule, fourth enforcement state, and lore-host ADR (#401)

### Fixed

- `autonomous-loop`: de-orphaned the per-item routing pointer when running AFK (#406)
- `setup-dividedby-skills`: corrected Conventions block section list (#388)
- Reusable-loop caller stubs now grant `issues:write` permission (#384)
- `skill-divergence-audit`: aligned stated cap to 2 (#376)

### Removed

- ADR-index generator and its drift guard (#377)
