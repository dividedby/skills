# Changelog

All notable changes to this project's two published surfaces — the skills catalog and the `harness/` Python — are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Top-level CHANGELOG.md (#397)
- CODING_STANDARDS.md (#398)
- docs/agents/skill-authoring.md (#405)

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
