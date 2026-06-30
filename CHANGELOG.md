# Changelog

All notable changes to this project's two published surfaces — the skills catalog and the `harness/` Python — are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/).

## [Unreleased]

### Added

- `council`: blind, diverse multi-persona panel skill — three-round structure (blind parallel evaluation → anonymized peer-rank → chair synthesis on opus); 8-persona roster (Falsifier/opus, Minimalist/sonnet, Pragmatist/opus always-on; Operator, Convention Keeper, Security, Performance, Frontend-UX-a11y conditional); Security hard-floored on auth/payments/secrets/migrations; structured output contract with mandatory Panel Dissent block; first skill in the catalog to drive the built-in Workflow tool (ADR 0036, #492)
- ADR 0036: skills may drive the built-in Workflow tool; `/council` is the reference pattern — disambiguates the Workflow-tool orchestration primitive (parallel/pipeline/agent) from the scheduled `claude -p` proposal-loop sense of "workflow"; establishes four authoring rules for any future skill that drives it (#492)
- `check-idea-inbox-drift`: fleet-wide, report-only idea-inbox.md structural drift detector; weekly cron Sun 06:00 UTC (staggered 1h after label-drift); checks eight canonical anchors (breadcrumb, six drain steps, rolling-window section) per carrier repo and files one `idea-inbox-drift` issue naming `setup-dividedby-skills` as the fixer; graceful no-op when `ISSUES_TOKEN` is absent; references #489 for one-time reconciliation (#488)
- `write-well`: lean English-only draft + de-slop skill — two entry points (`draft`: blank-page to polished via core-finding, structure, and the F3 de-slop layer; `improve`: bring-your-own-text via structure-check, density, and de-slop); three files total (SKILL.md + two reference docs in `references/`); ADR 0035 scoped exception to ADR 0024 (#470)
- `setup-dividedby-skills` Concern G (Changelog): onboards a repo's changelog support in one run — seeds or repairs a Keep a Changelog 2.0.0 `CHANGELOG.md` (creating one with a git-history-seeded `## [Unreleased]` draft behind the HITL gate, or mechanically fixing URL / missing-`[Unreleased]` / dead-1.x-anchor drift without rewriting past entries), copies the fleet `docs/agents/changelog-guideline.md`, and enrolls the repo in the centralized evaluator; idempotent — a re-run on a conforming, already-enrolled repo makes zero changes (#458)
- Centralized weekly changelog-health evaluator: `changelog-health.yml` workflow + `harness/prompts/changelog-health.md` prompt — flag-not-rewrite advisory loop (reads `CHANGELOG.md` against recent `git log` and the eight-row grading checklist in `docs/agents/changelog-guideline.md`; proposes `## [Unreleased]` lines and rubric citations; never edits `CHANGELOG.md`; not a CI gate); proven on the skills repo; harness read from local checkout (ADR 0014); budget backstop $3.00 (ADR 0019) (#457)
- `docs/agents/changelog-guideline.md` — fleet CHANGELOG quality rubric distilling Keep a Changelog 2.0.0 (six-category taxonomy, `## [Unreleased]` discipline, the 2.0.0 conventions); every rule is phrased as a check against a `git log` + changelog diff so the doc doubles as the #457 evaluator's grading criteria (ADR 0034, #456)
- ADR 0034: fleet changelogs are hand-maintained + LLM-evaluated, not semantic-release — extends #397's hand-maintained choice fleet-wide and layers on a weekly flag-not-rewrite evaluator nudge; rejects semantic-release (a release-pipeline gate vs the maintainer's anti-gate constraint; changelog generation not cleanly modular; fleet-wide conventional-commits unwarranted) (#456)
- `autonomous-loop/EVALUATOR-GATE.md` — evaluator-gate detail (generator/evaluator split, rubric design, calibration, sprint contracts, cost heuristics) disclosed from `SKILL.md` element 6 to a supporting doc, cutting SKILL.md sprawl (#448)
- `autonomous-loop/FIREWALL.md` — generic context-hygiene supporting doc (per-item sub-agent, budget checkpoint, compaction, flush/drop); pointable by any multi-item skill, loop or loopless; migrated from `context-firewall` (ADR 0033, #448)
- ADR 0033: context-firewall folds into autonomous-loop as a supporting doc (`FIREWALL.md`), not a standalone skill — supersedes ADR 0012 (the predicted standalone loopless invoker never materialized); the firewall *knowledge* is kept while the standalone trigger is dropped; de-registration + doc re-cut tracked in #448 (#446)
- ADR 0032: consolidate three write PATs (`SKILLS_TRACKER_TOKEN`, `DRIFT_CHECK_TOKEN`, unused agent-research write PAT) into one `ISSUES_TOKEN` (all repos, Issues:RW + Contents:read); host/consumer mode becomes the explicit `is-tracker-host` workflow input read by `cli.py` as `IS_TRACKER_HOST` (not token presence); the `repo == dividedby/skills` swap guard in `cli.py` is retained and gains importance with the wider token scope; Option-B fallback keeps existing secrets working during transition (#424)
- `check-label-drift`: fleet-wide, report-only label-doc drift detector (mirrors `check-workflow-drift`); weekly cron Sun 05:00 UTC; classifies four drift shapes per consumer repo and files one `label-drift` issue naming `setup-dividedby-skills` as the fixer; graceful no-op when `DRIFT_CHECK_TOKEN` is absent (#415)
- Top-level `CHANGELOG.md` — tracks all notable changes to the two published surfaces (the skills catalog and `harness/` Python) in Keep a Changelog format (#397)
- `CODING_STANDARDS.md` — authoring and code-style rules for markdown skills and `harness/` Python (#398)
- `docs/agents/skill-authoring.md` — composition patterns and editorial-judgement examples (ADR 0002 edge cases) for authoring new skills (#405)

### Removed

- `dividedby/bench` archived (read-only since 2026-06-21) and dropped from the `check-idea-inbox-drift` fleet detector's `REPOS` map — an archived carrier can't be reconciled, so flagging it would file an un-fixable `idea-inbox-drift` issue; matches the script's "archived repos dropped by hand" policy (#489)
- `context-firewall` skill retired — de-registered from `plugin.json`, top-level `README.md`, and `skills/engineering/README.md`; directory deleted; knowledge preserved in `autonomous-loop/FIREWALL.md` (ADR 0033, #448)
- **Breaking:** Option-B dual-secret fallbacks removed now that `SKILLS_TRACKER_TOKEN` and `DRIFT_CHECK_TOKEN` are decommissioned (ADR 0032 cutover complete) — consumer repos must use `ISSUES_TOKEN`: `apply-agent-research-reusable.yml` drops the `SKILLS_TRACKER_TOKEN` secret declaration and fallback; `check-workflow-drift.yml` and `check-label-drift.yml` rename the env var to `ISSUES_TOKEN` and drop the `DRIFT_CHECK_TOKEN` fallback; docstrings and NOTICE messages in `check_workflow_drift.py` and `check_label_drift.py` simplified accordingly
- `tweakcc-maint` archived and decommissioned: dropped from the workflow-drift and label-drift fleet detectors; ADR 0014 updated to reflect that the reusable-rail migration (ADR 0029) covers the active consumer fleet only (moodreader, agent-research, goodreads-bot + skills canary) (#416)

### Changed

- `repo-audit`: Stage 2 leverage hunt deepened into a blind five-persona Workflow panel — Deletionist, Performance Analyst, Architect, Capability Scout, and Convention & Backlog Keeper each sweep the codebase independently via `parallel()`, followed by an anonymized cross-review/dedup round before synthesis; panel lineup and per-persona rationale are logged before the panel runs; degrades gracefully to the prior sequential four-category hunt when the Workflow tool is unavailable; Stage 3 contract (reconcile-against-backlog hard gate, altitude bar, roadmap) unchanged; reuses the `/council` blind + anonymized-peer-rank mechanism (ADR 0036, #497)
- `software-design`: advisory `/council` sub-step wired at the Step 6→8 seam — after the user confirms the module map and before issue carving; council receives the confirmed design and the strongest open objections, appends its Panel Dissent block for human review, and degrades gracefully (skip noted, design proceeds) if the Workflow tool is unavailable or the invocation fails (#494)
- `doc-it`: generated reference docs now get a prose-quality pass through `write-well` before they are applied — README, API, and onboarding drafts receive the full structure-plus-de-slop pass, and CHANGELOG drafts receive the lighter voice subset (density, typographic tells, evidence-bound); doc-it's scan/audit behaviour and its ADR / `CONTEXT.md` report-only boundary are unchanged (ADR 0022, #472)
- `setup-dividedby-skills` Concern G: seeded `## [Unreleased]` entries now run through `write-well`'s de-slop voice rules (sentence-load density, typographic tells, evidence-bound) before the HITL review, so a freshly scaffolded changelog reads in plain consumer voice (rubric Rule 2); narrative-structure rules are deliberately excluded for one-line entries (#473)
- `changelog-health` evaluator fanned out from 1 to 6 enrolled repos — listed in `harness/changelog-health/enrolled-repos.txt` (one `owner/repo` per line, `#`-comments and blank lines ignored; enroll a repo by adding a line, no workflow edit needed) — via a GitHub Actions matrix, one job per repo per weekly run; an empty or all-comments list skips the run instead of erroring; single-open-advisory dedup moved from the agent prompt into `cli.py publish` (`--dedup-open`); the agent now runs no `gh` and holds no write credential (default token is `contents: read` only) (#458)
- `workflow-onboarding`: `source:changelog-health` added to the canonical LOOP label set — repos onboarded after this change get the label provisioned automatically (#461)
- `autonomous-loop` supporting docs tightened for sprawl: `FIREWALL.md` dedups the vocabulary/body overlap, the repeated "compact return" statement, the §3/§4 forced-compaction restatement, and the anti-patterns list; `RUNNING-AFK.md` binds the apply-and-merge gate constraints to guardrails 2–4 by reference; `EVALUATOR-GATE.md` no-op prune (#448)
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
- `apply-agent-research` prompt: candidate log step (5a) emits one line per KB candidate to the Actions step summary — target surface plus advanced/dropped reason — so pre-gate reasoning is visible alongside outcomes (#421)
- `apply-agent-research` cli.py: `find-open` subcommand for cross-repo dedup reads without a bare `gh` call (#418)
- `project-claude-config`: detect situational sections and propose `<important if>` gating (#399)
- `project-claude-config`: detect label-doc drift and hand off to `setup-dividedby-skills` (#402)
- `setup-dividedby-skills`: add must-fix outcome + force-canonical mode for drifted label conventions (#393)
- proposal-loop reusable workflows: SHA-pin actions, drop acceptEdits, scope allowedTools; Dependabot for actions (#394)
- `apply-agent-research` folds onto the claude-loops-v1 reusable rail: one `workflow_call` body (`apply-agent-research-reusable.yml`) replaces the active consumers' full-copy envelopes; each repo vendors a thin caller stub; hardened (no acceptEdits, scoped allowedTools, SHA-pinned checkout); ADR 0029 (#417)
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
