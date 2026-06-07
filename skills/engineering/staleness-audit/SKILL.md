---
name: staleness-audit
description: >
  Audit a repo's pinned toolchain versions for staleness and emit a ranked
  report — the complement to Dependabot's library bumps. Safe in-major bumps are
  auto-applied behind a verify gate; cross-major / EOL jumps stay recommendations.
  Use when asked to check whether a project's language/runtime pins (Node, and
  later the wider ecosystem) have fallen behind, or to stand up a monthly review.
---

# Staleness Audit

This skill audits the versions a repo **pins its toolchain to** — the runtime and
language versions in dotfiles and manifests — and reports which have fallen
behind upstream. It is the deliberate complement to Dependabot: Dependabot bumps
**library dependencies** inside a manifest; this audit covers the **toolchain
pins** Dependabot leaves alone (`.nvmrc`, `engines`, language-version files).

The skill has one spine, and every later capability thickens a station on it
rather than adding a new path:

**scan → classify → validate → apply → render → register**

It walks the **Node toolchain pins**, resolves each finding against upstream to
fill in latest version / EOL / migration, then — and only behind a verify gate —
auto-applies the *safe* (in-major) bumps one at a time, reverting any that break
the build, and emits a single urgency-ranked report of what was applied and what
is still recommended.

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

### Apply — verify-gated, one safe bump at a time

Only the **safe** bumps are auto-applied, and only behind a working verify gate.
The decision "may this finding be auto-applied, and if not, what downgrade?" is a
pure decision — it must not depend on model judgment, or a cross-major or EOL jump
could slip into an unattended apply — so it lives as executable code:
[`lib/apply_policy.py`](lib/apply_policy.py) (`decide(finding)`). Call it per
finding; never re-derive the gate in prose. This station owns only the *mechanics*
the agent executes around that decision.

**Discover the verify command** in priority order, preferring the CI sequence so
the gate matches what the project actually trusts as green:

1. `package.json` `scripts` (`test`, `lint`, `build`, `typecheck` — run what's
   defined).
2. `Makefile` targets (`make test`, `make check`).
3. CI verify steps — the commands a workflow runs on PRs (`.github/workflows/*`).
4. A language default as a last resort (`npm test`, `npm ci && npm test`).

Prefer the CI sequence: if CI runs `npm ci && npm run lint && npm test`, that is
the verify command — a bump is only "green" if it passes what CI would.

**If no verify command is discoverable, auto-apply is disabled** — there is no way
to prove a bump is safe. Every finding downgrades to **`unverified: no verify
command`** and the report is recommend-only. `apply_policy.decide` enforces this:
with `verify_available=False` it returns that reason for *every* finding,
regardless of gap.

**With a verify command, apply one bump at a time.** For each finding, in urgency
order, ask `apply_policy.decide`; act only on `"apply"`. Then, per bump:

1. Edit the single owned pin file to the new in-major version — **one bump only**.
2. Run the verify command.
3. **Pass:** keep the edit; record the finding as **applied** (feed
   `verify_passed=True`).
4. **Fail:** **revert that single edit** and downgrade the finding to
   **`recommended (verify failed)`** (`apply_policy.decide` returns exactly this
   for an otherwise-eligible bump with `verify_passed=False`). Carry on to the next
   bump — one failing bump never blocks the others.

Never batch bumps: a batched verify can't tell you *which* bump broke. One edit,
one verify, one keep-or-revert.

**Never auto-apply a cross-major or EOL-driven jump.** A `major` gap and any
past-EOL pin stay recommendations carrying the researched migration path — the safe
upgrade runs *through* that migration, which is not a mechanical bump.
`apply_policy.decide` returns `recommended: cross-major` / `recommended: eol jump`
for these and never `"apply"`, even on a green verify. Likewise an **unverified**
finding (web was down, per the validate station) is never applied — it has no
trustworthy `latest` to bump to.

### Render — one urgency-ranked report

Emit a single markdown table, one row per finding, with these columns:

```
target | file | current | latest | gap | EOL | risk | action | migration
```

`latest`, `EOL`, and `migration` carry the validated values, or `unverified: no
web access` when the lookup could not run. Order the rows **most-urgent-first**
via [`lib/rank.py`](lib/rank.py) — a pure, tested helper that ranks past-EOL pins
to the top, then by gap severity — so the ordering is reproducible and not a
per-run judgment call.

Lead the report with an **Applied** section listing each bump the apply station
applied and verified green — `target`, the `current → new` versions, the file, and
the verify command that passed. This is the proof the maintainer reviews; if no
bump was applied (or auto-apply was disabled), say so explicitly. The table below
then carries the remaining findings, whose `action` is a recommendation —
including any downgraded to `recommended (verify failed)` or, when no verify
command was found, every finding as `unverified: no verify command`.

### Register

The skill is registered in `.claude-plugin/plugin.json` and linked from the
top-level `README.md`, per repo convention (the `check-skill-registration` Stop
hook enforces it).

## Scope at this slice

- **Node toolchain pins only.** Python/Go/CI-matrix/container coverage is a later
  station on the same `scan` step, not a different skill.
- **Auto-apply only the safe, verified bumps.** In-major (patch/minor) bumps on
  owned files are applied behind a verify gate, one at a time, with per-bump
  revert. Cross-major / EOL jumps and any unverified finding are recommend-only —
  the apply station may only ever act on a *verified* finding it can prove green.

## Anti-Patterns

- **Re-deriving the gap, the ranking, or the apply gate in prose.** All three are
  tested pure functions ([`version_gap.py`](lib/version_gap.py),
  [`rank.py`](lib/rank.py), [`apply_policy.py`](lib/apply_policy.py)); call them.
- **Guessing a version or EOL when web is down.** Degrade to `unverified: no web
  access` and suppress apply — never fabricate upstream data.
- **Auto-applying a cross-major or EOL jump.** These carry breaking-change
  migration; they are recommendations, never mechanical bumps — let
  `apply_policy.decide` gate it.
- **Bumping without a verify gate, or batching bumps.** No discoverable verify
  command means no apply at all. With one, apply a single bump per verify so a
  failure pins to the bump that caused it; keep on pass, revert on fail.
- **Hardcoding a file catalogue as the rule.** Pins are a concept; match the
  repo's real layout, with the common files as illustrative starting points
  (ADR 0002).
- **Overlapping Dependabot.** Library bumps are Dependabot's job; this audit is
  for the toolchain pins it does not touch.
