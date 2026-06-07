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

**scan → classify → validate → render → register**

It walks the **Node toolchain pins**, resolves each finding against upstream to
fill in latest version / EOL / migration, and emits a single urgency-ranked,
**recommend-only** report. The audit observes and recommends — it never mutates
the repo at this stage (auto-apply is a later slice).

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

The gap is computed against the `latest` resolved by the next station. The
classifier is unit-tested ([`lib/version_gap.test.py`](lib/version_gap.test.py)),
so the only non-deterministic input to a finding's classification is the upstream
`latest` the validate step fetches.

### Validate — resolve each finding against upstream

For each finding, confirm three things from upstream, using web search/fetch:

- **latest** — the current stable release of that toolchain (`Node 22.x`).
- **EOL** — fetch the pinned major's end-of-life **date**, then decide pastness
  with [`lib/eol.py`](lib/eol.py) (`is_past_eol(date, today)`), not by asking the
  model "is this past EOL?" — it anchors on the data's vintage and gets it wrong.
  A pin past EOL is the top risk regardless of how far behind it is — security
  fixes have stopped. Feed the result as `eol_passed` to the ranking helper.
- **migration** — the canonical upgrade note / changelog link to carry in the
  report so the reader (or a later auto-apply slice) has the path in hand.

Prefer authoritative sources — the project's own release page or a maintained
EOL dataset (e.g. `endoflife.date`) over a blog. Resolve `latest`, feed it to
[`lib/version_gap.py`](lib/version_gap.py) for the real gap, and record
`eol_passed` per finding.

**Web is a dependency, not a guarantee — degrade, never guess.** When web access
is unavailable or a lookup fails, do **not** invent a version or EOL date. Emit
the finding with `latest`/`EOL`/`migration` left as **`unverified: no web
access`**, and **suppress any apply path** for it — an unverified finding is a
recommendation only, never something a later slice may auto-apply. A partial
audit that is honest about what it could not verify beats a confident wrong one.

### Render — one urgency-ranked, recommend-only report

Emit a single markdown table, one row per finding, with these columns:

```
target | file | current | latest | gap | EOL | risk | action | migration
```

`latest`, `EOL`, and `migration` carry the validated values, or `unverified: no
web access` when the lookup could not run. Order the rows **most-urgent-first**
via [`lib/rank.py`](lib/rank.py) — a pure, tested helper that ranks past-EOL pins
to the top, then by gap severity — so the ordering is reproducible and not a
per-run judgment call. Every `action` is a recommendation; there is **no apply
path here**, and unverified findings are explicitly never auto-applied.

### Register

The skill is registered in `.claude-plugin/plugin.json` and linked from the
top-level `README.md`, per repo convention (the `check-skill-registration` Stop
hook enforces it).

## Scope at this slice

- **Node toolchain pins only.** Python/Go/CI-matrix/container coverage is a later
  station on the same `scan` step, not a different skill.
- **Validate, but never mutate.** Upstream resolution (latest/EOL/migration) is in
  scope; any **auto-apply is not** — this slice stays observe-and-recommend. The
  apply path is a later slice, and it may only ever act on a *verified* finding.

## Anti-Patterns

- **Re-deriving the version gap or the ranking in prose.** Both are tested pure
  functions ([`version_gap.py`](lib/version_gap.py), [`rank.py`](lib/rank.py));
  call them.
- **Guessing a version or EOL when web is down.** Degrade to `unverified: no web
  access` and suppress apply — never fabricate upstream data.
- **Mutating the repo.** This slice is recommend-only — emit a report, change
  nothing.
- **Hardcoding a file catalogue as the rule.** Pins are a concept; match the
  repo's real layout, with the common files as illustrative starting points
  (ADR 0002).
- **Overlapping Dependabot.** Library bumps are Dependabot's job; this audit is
  for the toolchain pins it does not touch.
