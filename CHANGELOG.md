# Changelog

All notable changes to this project's two published surfaces — the skills catalog and the `harness/` Python — are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `autonomous-loop/FIREWALL.md` — generic context-hygiene supporting doc (per-item sub-agent, budget checkpoint, compaction, flush/drop); pointable by any multi-item skill, loop or loopless; migrated from `context-firewall` (ADR 0033, #448)
- ADR 0033: context-firewall folds into autonomous-loop as a supporting doc (`FIREWALL.md`), not a standalone skill — supersedes ADR 0012 (the predicted standalone loopless invoker never materialized); the firewall *knowledge* is kept while the standalone trigger is dropped; de-registration + doc re-cut tracked in #448 (#446)
- ADR 0032: consolidate three write PATs (`SKILLS_TRACKER_TOKEN`, `DRIFT_CHECK_TOKEN`, unused agent-research write PAT) into one `ISSUES_TOKEN` (all repos, Issues:RW + Contents:read); host/consumer mode becomes the explicit `is-tracker-host` workflow input read by `cli.py` as `IS_TRACKER_HOST` (not token presence); the `repo == dividedby/skills` swap guard in `cli.py` is retained and gains importance with the wider token scope; Option-B fallback keeps existing secrets working during transition (#424)
- Removed Option-B dual-secret fallbacks now that `SKILLS_TRACKER_TOKEN` and `DRIFT_CHECK_TOKEN` are decommissioned (ADR 0032 cutover complete): `apply-agent-research-reusable.yml` drops `SKILLS_TRACKER_TOKEN` secret declaration and fallback; `check-workflow-drift.yml` and `check-label-drift.yml` rename env var to `ISSUES_TOKEN` and drop `DRIFT_CHECK_TOKEN` fallback; docstrings and NOTICE messages in `check_workflow_drift.py` and `check_label_drift.py` simplified accordingly

### Removed

- `context-firewall` skill retired — de-registered from `plugin.json`, top-level `README.md`, and `skills/engineering/README.md`; directory deleted; knowledge preserved in `autonomous-loop/FIREWALL.md` (ADR 0033, #448)

### Changed

- `autonomous-loop` SKILL.md rewritten to the /writing-great-skills standard; `/flow-pr` wired as the per-item close-out at the apply-and-merge-on-green end of the gate spectrum; RUNNING-AFK.md flush/drop deduped to FIREWALL.md (#448)
- `/context-firewall` cross-references in `autonomous-loop/SKILL.md`, `autonomous-loop/RUNNING-AFK.md`, and `docs/agents/skill-authoring.md` repointed to `FIREWALL.md`; `context-firewall` token removed from `docs/agents/installed-skills.md` (#448)
- `docs/onboarding/` corrected to post-amendment ADR 0019 regime: cadence updated to 3×/week Mon/Wed/Sat (`* * 1,3,6`), per-run cap updated to ≤2 issues, per-channel cap framing replaced with shared-budget language (one budgeted gate pass, ADR 0019 superseded ADR 0011) (#440)
- `CONTEXT.md` Guard hook definition: appended output convention (silent on pass, diagnostic-to-stderr on block) (#441)
- `apply-agent-research` cli.py `_gh_env`: reads `ISSUES_TOKEN` instead of `SKILLS_TRACKER_TOKEN`; module-level token invariant comment updated
- `apply-agent-research` cli.py `_mode`: explicit-flag contract — `IS_TRACKER_HOST=true` → `host`, anything else/unset → `consumer`; replaces token-presence discriminator (ADR 0032)
- `apply-agent-research-reusable.yml`: added `is-tracker-host` input; added `ISSUES_TOKEN` secret declaration; credential env line uses `ISSUES_TOKEN || SKILLS_TRACKER_TOKEN` fallback; exported `IS_TRACKER_HOST` to job env; header comment updated
- `apply-agent-research.yml` (host caller): passes `is-tracker-host: true`; no tracker token secret (host writes to itself with `GITHUB_TOKEN`)
- `check-workflow-drift.yml`, `check-label-drift.yml`: credential env uses `ISSUES_TOKEN || DRIFT_CHECK_TOKEN` fallback; header comments updated
- `tools/check_workflow_drift.py`, `tools/check_label_drift.py`: renamed `DRIFT_CHECK_TOKEN` → `ISSUES_TOKEN` in docstrings and NOTICE messages
- `harness/prompts/apply-agent-research.md`: discriminator rationale updated (explicit flag, not token absence); `$SKILLS_TRACKER_TOKEN` refs → `$ISSUES_TOKEN`
- Docs (`skill-request-flow.md`, `skill-promotion-flow.md`, `consumer-setup.md`, `proposal-loop-harness.md`, `staleness-setup.md`, `arch-review-setup.md`, `vendored-workflows.md`): `SKILLS_TRACKER_TOKEN`/`DRIFT_CHECK_TOKEN` → `ISSUES_TOKEN`; presence-discriminator framing → explicit-flag framing
- ADR 0031: cross-repo Actions tokens are per-role fine-grained PATs — cost-scrape consolidates to a single `ACTIONS_TOKEN` scoped to all repositories (current and future) for zero-touch onboarding; tracker-write and drift-read stay repo-scoped; rejects classic PAT and GitHub App; org secrets unavailable on a User account (#424)
- `check-label-drift`: fleet-wide, report-only label-doc drift detector (mirrors `check-workflow-drift`); weekly cron Sun 05:00 UTC; classifies four drift shapes per consumer repo and files one `label-drift` issue naming `setup-dividedby-skills` as the fixer; graceful no-op when `DRIFT_CHECK_TOKEN` is absent (#415)
- `apply-agent-research` prompt: candidate log step (5a) emits one line per KB candidate to the Actions step summary — target surface plus advanced/dropped reason — so pre-gate reasoning is visible alongside outcomes (#421)
- `apply-agent-research` cli.py: `find-open` subcommand for cross-repo dedup reads without a bare `gh` call (#418)
- Top-level CHANGELOG.md (#397)
- CODING_STANDARDS.md (#398)
- docs/agents/skill-authoring.md (#405)
- `project-claude-config`: detect situational sections and propose `<important if>` gating (#399)
- `project-claude-config`: detect label-doc drift and hand off to `setup-dividedby-skills` (#402)
- `setup-dividedby-skills`: add must-fix outcome + force-canonical mode for drifted label conventions (#393)
- proposal-loop reusable workflows: SHA-pin actions, drop acceptEdits, scope allowedTools; Dependabot for actions (#394)
- `apply-agent-research` folds onto the claude-loops-v1 reusable rail: one `workflow_call` body (`apply-agent-research-reusable.yml`) replaces the active consumers' full-copy envelopes; each repo vendors a thin caller stub; hardened (no acceptEdits, scoped allowedTools, SHA-pinned checkout); ADR 0029 (#417)
- `tweakcc-maint` archived and decommissioned: dropped from the workflow-drift and label-drift fleet detectors; ADR 0014 updated to reflect that the reusable-rail migration (ADR 0029) covers the active consumer fleet only (moodreader, agent-research, goodreads-bot + skills canary) (#416)
- `autonomous-loop`: added non-binary-quality evaluator gate section (generator/evaluator split, rubric design, calibration, sprint contracts, cost heuristics) (#430)

### Fixed

- Consumer cross-repo `skill-request`/`skill-promotion` filing silently no-opped under the hardened scoped `--allowedTools` introduced in #394: the `GH_TOKEN="$SKILLS_TRACKER_TOKEN" gh …` env-prefix was denied by the allowlist. cli.py now selects `SKILLS_TRACKER_TOKEN` itself for any `--repo dividedby/skills` call (`find-open`/`file`/`comment`) — no env-prefix, no token value in the shell, no tag move required (#418)
- Consumer-mode detection also broke under the scoped allowlist: the agent could not inspect `$SKILLS_TRACKER_TOKEN` via `printenv`, `env`, shell expansion, or `python3 -c` — all denied by the sandbox. Fixed via the allowlist-safe `cli.py mode` subcommand (prints `host` or `consumer`, never the token value) (#418)
- `apply-agent-research` prompt: steered agent away from denied shell helpers (`cat`, piped `grep`, `echo`/`tee`, `python3 -c`) toward the allowlisted built-in tools (`Read`, `Grep`, `Write`, `gh --jq`, `cli.py` subcommands) to prevent incidental approval denials in unattended runs (#427)

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
