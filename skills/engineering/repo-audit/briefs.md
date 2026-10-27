# Repo Audit — Lens Briefs

One brief per lens. Stage 3 adapts each to the project: fill the bracketed
parts from the Stage 1 profile, drop bullets that do not apply to the stack,
and add the user's focus. Every brief also carries the shared header below.

## Shared header (every lens)

- What the project is in one sentence, its stack and platform target.
- Repo path, branch and pinned commit; "confirm the commit you read".
- The read-only rule from `SKILL.md`, restated in full. Name what *is*
  allowed (build and test into ignored output, read-only `gh` calls, scratch
  packages outside the repo).
- The size facts: lines per area, the largest files, test count and run time.
- Output: the full report as Markdown at a named scratchpad path, then a short
  summary reply (top findings, under 500 words).
- Finding shape: severity (High / Med / Low), evidence (`file:line`, command
  and result, or URL), why it matters, fix plan (no edits), effort (S / M / L).
  Rank by impact.

## Code and performance

Focus on cost at realistic scale and on correctness risk:

- **Scale.** Pick the sizes a heavy real user reaches (records, files,
  requests) and look for super-linear work: nested matching, repeated full
  scans, whole-file rewrites inside loops, repeated parse/serialize of state,
  full payloads where summaries would do.
- **Measure, don't guess.** Build a scratch benchmark outside the repo that
  depends on it by path, generate synthetic data at two sizes, and time the hot
  paths. Report measured numbers with how they were made; mark projections.
- **Concurrency.** Isolation and threading rules of the stack, work on the UI
  thread that should not be, unstructured tasks, cancellation that does not
  reach long loops, races between subsystems.
- **I/O.** Write frequency, durability versus cost, journal and log growth,
  backup or export cost, memory held at once.
- **External APIs.** Batching where the API offers it, paging, rate limits and
  backoff, request methods, timeouts, per-item fallbacks.
- **Structure.** Dead code, duplicated logic, types that do too much.
- **Errors.** Swallowed failures (`try?`, empty catches), failures that leave
  state half-written.
- **Tests.** Run time, sleeps and timing-based flakiness, risky paths with no
  test, missing scale tests.

## Architecture, repo and docs

Start by verifying the profile's "known facts" (what docs, CI and release
tooling exist) rather than trusting them. Then assess:

1. **Module architecture.** Layering and dependency direction, god objects,
   test-only or demo code shipped in production targets, whether parts should
   be separate modules.
2. **Security and privacy.** Credential and token storage, auth flow, scopes or
   permissions requested versus used, sandboxing and entitlements (or the
   stack's equivalent), where personal data lands on disk and with what
   permissions. Search history for secrets; report presence only, never values.
3. **Build and release.** Signing, notarization or store path, update channel,
   versioning, reproducibility.
4. **CI.** A concrete workflow plan for the stack (test, build, lint, caching),
   and any runner availability problem for the platform version targeted.
5. **Documentation.** Outlines for what is missing (README, architecture,
   contributing, changelog convention); quality of in-code docs on a sample of
   about ten files.
6. **Repo settings and hygiene.** Via read-only `gh api`: licence, description,
   topics, branch protection, ignore rules, fixture hygiene, history size.

## Design

Runs only with a UI. The reviewer is a senior product designer for the
platform; the bar is first-class platform-native or top-tier third-party
software. Name three to six apps in the same category to compare against.

- **Inputs.** Every Stage 2 capture (list the paths; read them all), icons and
  other visual assets, and the UI source.
- **Research.** The platform's current interface guidelines for the patterns
  the product uses: windows and navigation, toolbars, settings, menus or menu
  bar items, onboarding, destructive actions, progress, empty states,
  accessibility.
- **Per screen.** Information hierarchy, layout and spacing, type scale,
  colour and custom components versus system ones, control choice, toolbar
  use, empty / loading / error states, copy tone and length, keyboard
  navigation, screen-reader labels, text scaling, contrast in both
  appearances (read the code for the appearance not captured).
- **App level.** Navigation structure and what the home screen should be,
  where settings and first-run belong, grouping of secondary tools,
  notifications, how review or editing flows compare with the platform's own
  apps.
- **Deliverables.** (1) The report: per-screen issues with severity, a concrete
  redesign and the platform APIs to use; app-level recommendations. (2) A
  mockup spec for four or five key screens — layout regions, components, exact
  copy, states, light and dark colour notes — precise enough to render as HTML
  without guessing.

## Market and research

The repo is context only. Use web search (standard first, extended when thin)
and page fetches.

1. **Competitors and prior art.** Commercial and open source; for each, the
   approach, features, price and common complaints.
2. **What users say.** Forums and Reddit communities for the platform and
   problem space. One short quote per source (under 15 words) with its URL.
3. **Technical gotchas.** Quotas, token or cursor expiry, platform permissions
   and entitlements, format limits — whatever others in this space hit.
4. **Gaps and opportunities** versus the field.
5. **Projects worth copying** for structure, polish, README, CI and release:
   repo URLs and what to copy.

Cite everything; mark what could not be verified.
