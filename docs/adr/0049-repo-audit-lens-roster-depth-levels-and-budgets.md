# Repo-audit runs a five-lens roster at two depths against stated budgets

> **Status: Accepted** — maintainer decision (2026-11-23). **Amends [ADR 0042](./0042-repo-audit-becomes-a-read-only-report.md).**

## Context

ADR 0042 fixed four lenses, Design and Market the only optional ones, and named
only a model per lens. Issue #638 (part of epic #611) revisits that after the
method issues landed. Three costed runs of the skill at `0a0cc06` showed gaps:

- **The roster has no single home.** Stage 1 lists Design and Market, `briefs.md`
  headings carry the models, and two briefs (Security, privacy and data; Product
  and docs conformance) were sub-headings of the "Architecture, repo and docs"
  brief with no model, so a run could count two lenses or three where there
  was one.
- **No agent type.** Only a model was given. Named read-only agent types lack
  Write, which every lens report file needs, and the market and architecture
  lenses need web tools.
- **The market trigger is ambiguous.** "When the project has users or
  competitors; internal tooling may skip it" ran the lens on a private
  single-user tool in the 2026-11-21 baseline: 113k tokens and 3 minutes, no
  Highs, nothing the plan used.
- **"Depth" and "budget" are undefined.** `SKILL.md` Stage 3, `run-log.md`,
  `probe.md` and `rubric.md` each defer to a depth budget that does not exist,
  so no lens has a ceiling and no run can say it is over budget.

## Decision

- **Five lenses, one parallel launch**, every lens a `general-purpose` agent
  (portable; has Write and the web tools). The table in `SKILL.md` is the one
  home for each lens's model, tools, owned areas and run condition; the
  `briefs.md` headings no longer carry a model.

  | Lens           | Model  | Owns                                                                        | Web tools |
  | -------------- | ------ | --------------------------------------------------------------------------- | --------- |
  | `code`         | sonnet | Code quality, Tests, Performance                                            | no        |
  | `architecture` | sonnet | Architecture, Tech stack, Security, Privacy, Data integrity, External facts | yes       |
  | `product`      | sonnet | Feature completeness, Repo organisation, Ops and release, Agent readiness   | no        |
  | `design`       | opus   | Accessibility, Content and branding, Usability (UI present only)            | yes       |
  | `market`       | sonnet | no area; evidence for External facts, Tech stack and the Research section   | yes       |

  Every lens also has Read, Grep, Glob, Bash and Write. The `rules.md` rows go
  to the lens that owns each row's area.

- **Market** runs only when the repo is public (a GitHub remote that says so;
  "unknown" counts as not public) and its docs, release or listing name users
  other than the owner. Private, local-only and single-user repos skip it, with
  the reason stated.
- **Depth: `quick` and `standard`.** The prompt sets it ("quick", "quick
  audit"); the default is `standard`; it is a profile row. `quick` launches the
  `code` and `architecture` lenses only, from static reading, the baseline digest
  and the fleet check: no instances, probe, benchmarks, faults, install or
  walkthroughs. Every area a skipped lens owns is "Not assessed (depth)", naming
  the lens. `standard` is the full method set under the tier's reading rule.
- **At most four lens agents at `standard`.** The core lenses are `code`,
  `architecture`, `product` and, when a UI is present, `design`. Market runs
  only when a slot is free; otherwise it is skipped with the reason "standard
  four-agent cap". The cap is hard: no prompt overrides it. Market owns no area,
  so no verdict is lost.
- **A rules-harvest helper.** Stage 1 may delegate `rules.md` to one pre-lens
  helper when the harvest sources (the rule and claim documents it reads) exceed
  about 1,000 lines (provisional). It is not a lens: not counted in the four, not
  in `lens_coverage`, logged as its own Agents row, its tokens in the run total.
  The main session still checks a source `file:line` on every row. Not allowed at
  `quick`.
- **Budgets and ceilings.** `SKILL.md` carries the budgets per lens, per tier and
  depth. A lens's ceiling is 1.5 times its budget row, in wall time and tokens, so
  "over budget by more than 50%" reads the same for a lens and for the run. A
  run over a budget by more than 50% says so on the page, in the run log and in
  the closing message. The stop, partial and retry rules from #630 are unchanged.
  Main-session context is reported, not budgeted: the harness gives a context
  size at a moment, not tokens per stage.
- **Unchanged.** The read-only rule, the stages, the baseline's gates and
  10-minute time-box, and the rubric's areas.

## Evidence

Three runs of the skill at `0a0cc06`, all at `standard` depth, started within the
same minute (23:43 CT, 2026-11-22) on one machine and ran at the same time, so
wall times may overstate a lone run. Lens figures are agent tokens and wall
minutes. Main-session context is **not** in the agent totals: 327k (infra) and
415k (marketplace, 83% of a 500k window) at the end; sideload's was not
recorded.

| Run                                                           | Tier         | Wall   | code          | architecture (one agent, ten areas) | design        | market       | Agent total                                     |
| ------------------------------------------------------------- | ------------ | ------ | ------------- | ----------------------------------- | ------------- | ------------ | ----------------------------------------------- |
| marketplace `b7fb8ca` (UI web app)                            | Medium       | 39 min | 281.3k / 12.6 | 259.5k / 8.9                        | 303.4k / 13.1 | 94.3k / 1.7  | 938.5k                                          |
| infra `9ee6434` (OpenTofu, shell, one Worker; no UI)          | Medium       | 32 min | 227k / 11.0   | 232k / 6.2                          | not launched  | not launched | 459k                                            |
| sideload `6b062b6` (CLI and menu bar app)                     | Large        | 35 min | 181k / 9.5    | 225k / 8.6                          | 166k / 7.8    | 112k / 2.3   | 830k (684k lenses + 146k harvest helper, 2 min) |
| baseline: marketplace `73d456e`, skills `1c78b1c`, 2026-11-21 | not recorded | 30 min | 222k          | 100k                                | 153k          | 113k         | 588k                                            |

Sideload's wall time is dominated by the baseline's 600 s test time-box; the
marketplace probe ran 34 cells in about 3 minutes.

Budgets (standard; tokens / wall) and what each came from:

| Row                  | Budget        | Derivation                                                                                                                                          |
| -------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| code                 | 300k / 15 min | Highest observed 281.3k / 12.6 min (marketplace), rounded up.                                                                                       |
| architecture         | 200k / 10 min | Provisional. The old single agent took 259.5k / 8.9, 232k / 6.2 and 225k / 8.6 for ten areas; this lens keeps six.                                  |
| product              | 150k / 8 min  | Provisional. The old agent's load split in two; the pair totals about 350k, about 100k over the old one, wall unchanged as the two run in parallel. |
| design               | 320k / 15 min | Highest observed 303.4k / 13.1 min (marketplace), rounded up.                                                                                       |
| market               | 120k / 3 min  | Highest observed 112k / 2.3 min (sideload).                                                                                                         |
| rules-harvest helper | 150k / 3 min  | 146k / 2 min (sideload).                                                                                                                            |

Totals at `standard`, Medium or Large: lenses 970k with a UI, 650k without
(770k with market). The whole run: 45 minutes with a UI (observed 39), 35 without
(observed 32), 40 on Large (observed 35). The Small-tier rows (half the per-lens
figures) and the `quick` rows have no costed run and are provisional.

## Consequences

- ADR 0042's "four lens agents at most" stays true at `standard`; `quick` runs
  two.
- Splitting the old architecture agent in two raises total tokens by about 100k
  against it for deeper reads per area, at no extra wall time.
- The `architecture` and `product` budgets, the Small-tier and `quick` rows, the
  helper threshold and the 60-cell probe cap are provisional: the #633 fixtures
  confirm or change them.
- Market is practically unreachable at `standard` on a public repo with a UI,
  because the four core lenses fill the cap. That is intended.
- Token ceilings may not be enforceable mid-run by the harness; wall time is. A
  ceiling that cannot be enforced degrades to a statement after the fact.
- The issue text names this ADR 0047; that number was taken by the untrusted-code
  ADR, so this is 0049.
