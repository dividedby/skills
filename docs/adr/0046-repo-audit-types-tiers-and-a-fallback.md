# Repo-audit adapts to repo type, size and shape

> **Status: Accepted** — maintainer decision (2026-11-21). **Amends [ADR 0042](./0042-repo-audit-becomes-a-read-only-report.md).**

## Context

ADR 0042 gave every repo one profile and one set of lens briefs. The maintainer's
repos span a userscript, an infra repo, a local web app, native tools and
servers, and "production ready" differs for each. A baseline run (2026-11-21)
showed the cost:

- The Code brief's "work on the UI thread" and `try?`, and the Architecture
  brief's signing, notarization and entitlements, were stripped by hand for a
  Python web app.
- The local-web-app checks (Host and Origin checks, a launcher on a fresh clone,
  isolated data for capture, ports) were written by hand.
- Line counts were misread: test fixtures held 7,600 of 22,877 test lines.

Nothing covered a repo of an unknown type, a docs-only repo, a monorepo, a repo
with no GitHub remote, or a repo too large to read in full.

## Decision

- **Types.** A new supporting file, `types.md`, is the one home for
  type-specific checks. Each entry lists how to detect the type, its added
  checks, the areas it usually skips and the brief bullets that apply only to it.
  Types are additive: a repo can carry several, and its applicable areas are the
  union. The native-app bullets move out of `briefs.md` into the native entry.
- **Fallback.** A repo, or part of one, matching no type gets a generic profile
  built from what is present. Its checks come from the repo's own docs and the
  16 areas. The page names the unrecognised type and the run log suggests an
  entry. A non-code repo gets the areas that apply to it: link integrity,
  accuracy against its sources, structure and freshness.
- **Size tiers.** Stage 1 sets Small, Medium or Large from tracked source lines
  (more than about 1,000 files raises the tier by one), after excluding
  vendored, generated and fixture files and stating the exclusions. On a large
  repo each lens samples, and ends its report with a coverage line that the page
  repeats. A sampled area is assessed on its sample; it is not "Not assessed".
- **Monorepos.** Stage 1 profiles each package, the scorecard gets a verdict per
  package as well as overall, and fleet rows that apply per package are checked
  per package. When the user names packages, only those are audited and the rest
  are Not assessed with the reason Not selected.
- **No GitHub remote.** Rows that need `gh api` are "not checked (no GitHub
  remote)"; the rest run. Any CI config counts as CI. A local-only repo counts
  as trusted.
- **Language.** Text in a non-space-delimited language gets counts only.
- **Unchanged.** The read-only rule, the four lenses, the six stages and the
  rubric's areas and severity scale. The lens roster, depth and budgets stay with
  dividedby/skills#638.

## Consequences

- `types.md` is a maintained file. A new type is a one-entry change, and an
  unrecognised type is reported so it can become one.
- Sampled coverage is stated per lens, not silent. `findings.json` gains
  per-lens coverage and a per-package scorecard, and the page gains the matching
  rows.
- `Not selected` joins the rubric's reason list; a missing GitHub remote reuses
  `Needs X`.
- The tier thresholds are approximate. They are revisited after a costed run
  under dividedby/skills#638.
