---
name: staleness-audit
description: >
  Audit a repo's pinned toolchain versions for staleness and emit a ranked,
  recommend-only report — the complement to Dependabot's library bumps. Use when
  asked to check whether a project's language/runtime pins (Node, and later the
  wider ecosystem) have fallen behind, or to stand up a monthly staleness review.
---

# Staleness Audit

This skill audits the versions a repo **pins its toolchain to** — the runtime and
language versions in dotfiles and manifests — and reports which have fallen
behind upstream. It is the deliberate complement to Dependabot: Dependabot bumps
**library dependencies** inside a manifest; this audit covers the **toolchain
pins** Dependabot leaves alone (`.nvmrc`, `engines`, language-version files).

The skill has one spine, and every later capability thickens a station on it
rather than adding a new path:

**scan → classify → render → register**

This first cut walks the **Node toolchain pins** and emits a single ranked,
**recommend-only** report. No web calls, no file edits — the audit observes and
recommends; it never mutates the repo at this stage.

## The spine

### Scan — find the pins, don't guess them

Read the files that actually carry a Node toolchain pin and extract the pinned
string verbatim:

- `.nvmrc` / `.node-version` — the whole file is the pin.
- `engines.node` in `package.json` — a semver range (`>=18`, `^20.11.0`).

Record each finding as `(target, file, current)` — what is pinned, where, and to
what. Scan only; resolving "latest" is a later station (it stays blank here).

Prescribe the **principle**, not a brittle file list: a pin is any place the repo
declares "build/run me on version X of this tool." Match the repo's real
conventions over a hardcoded catalogue — a monorepo may pin per-package.

### Classify — the gap is a pure decision, not prose

The size of each gap drives both the report's ranking and (in later slices) what
may be auto-applied, so it **must not depend on model judgment**. It lives as
executable code: [`lib/version_gap.py`](lib/version_gap.py), a pure stdlib helper
(ADR 0004) that maps a `(current, latest)` pair to `major | minor | patch | none
| unknown`. Invoke it by file path; never re-derive the gap math in prose.

At this slice `latest` is unknown (no web), so the gap column reads `unverified`
for every finding. The classifier is still wired in and unit-tested
([`lib/version_gap.test.py`](lib/version_gap.test.py)) so the later web slice only
has to feed it a real `latest`.

### Render — one ranked, recommend-only report

Emit a single markdown table, one row per finding, with these columns:

```
target | file | current | latest | gap | EOL | risk | action | migration
```

`latest`, `EOL`, and `migration` may be blank or `unverified` at this slice.
Every `action` is a recommendation — there is **no apply path here**. Rank
most-actionable first once gaps are known; with everything `unverified`, a stable
file order is fine.

### Register

The skill is registered in `.claude-plugin/plugin.json` and linked from the
top-level `README.md`, per repo convention (the `check-skill-registration` Stop
hook enforces it).

## Scope at this slice

- **Node toolchain pins only.** Python/Go/CI-matrix/container coverage is a later
  station on the same `scan` step, not a different skill.
- **No web, no mutation.** Resolving `latest`/EOL upstream and any auto-apply are
  later slices; this one is observe-and-recommend.

## Anti-Patterns

- **Re-deriving the version gap in prose.** The gap is a tested pure function;
  call it.
- **Mutating the repo.** This slice is recommend-only — emit a report, change
  nothing.
- **Hardcoding a file catalogue as the rule.** Pins are a concept; match the
  repo's real layout, with the common files as illustrative starting points
  (ADR 0002).
- **Overlapping Dependabot.** Library bumps are Dependabot's job; this audit is
  for the toolchain pins it does not touch.
