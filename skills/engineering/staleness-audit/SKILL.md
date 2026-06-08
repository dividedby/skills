---
name: staleness-audit
description: >
  Audit a repo's pinned toolchain versions for staleness and emit a ranked
  report — the complement to Dependabot's library bumps. Safe in-major bumps are
  auto-applied behind a verify gate; cross-major / EOL jumps stay recommendations.
  Use when asked to check whether a project's language/runtime pins (Node, Python,
  Go, container and CI matrices) have fallen behind, or to stand up a monthly review.
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

It walks the repo's **toolchain pins** across the ecosystem — Node, Python, Go,
asdf/mise, CI matrices, and container tags — resolves each finding against
upstream to fill in latest version / EOL / migration, then — only behind a verify
gate —
auto-applies the *safe* (in-major) bumps one at a time, reverting any that break
the build, and emits a single urgency-ranked report of what was applied and what
is still recommended.

## The spine

### Scan — find the pins, don't guess them

A pin is **any place the repo declares the version of a tool it builds or runs
on**. That is the rule. The files below are the illustrative v1 surface — the
common places that concept lands across ecosystems — not a frozen catalogue;
match the repo's real conventions over this list (a monorepo may pin per-package,
a shop may have its own dotfile). Read each, extract the pinned string verbatim,
and record `(target, file, current)` — what is pinned, where, and to what. Scan
only; resolving "latest" is a later station (it stays blank here).

**Two roles: a version you satisfy vs a floor you impose.** Tag each finding with
its role, because the two have *opposite* freshness goals and the apply gate keys
on it:

- **satisfy** — the version the repo itself builds or runs on (`.nvmrc`,
  `.tool-versions`, the `go` directive, a CI matrix entry, a `FROM` tag). Here
  fresh means *toward latest*; falling behind is the staleness. This is the
  default role and the one the rest of the spine is written for.
- **impose** — a *floor* the repo publishes for its **consumers** to satisfy
  (`engines.node` / `engines.npm`, `devEngines`, the lower bound of
  `requires-python`, peer-dependency ranges). A floor's goal is the **opposite**:
  keep it as *low* as the repo can still support, so the most consumers can use
  it. "Behind latest" is therefore **not** staleness for a floor — raising it
  sheds consumers. Record it `is_floor`; its disposition is decided differently at
  classify, validate, and apply.

**Node** — `.nvmrc` / `.node-version` (the whole file is the pin, a *satisfy*
version); `engines.node` / `engines.npm` / `devEngines` in `package.json` (a
semver range like `>=18`, `^20.11.0` — an `impose` **floor**, not a version the
repo runs on).

**Python** — `.python-version` (*satisfy*); `requires-python` in `pyproject.toml`
or `setup.cfg` (its **lower bound** is an `impose` floor; an upper cap is a
support ceiling, not staleness); `runtime.txt` (a `python-3.x` line, *satisfy*);
the `python_version` / `envlist` hints in `tox.ini`.

**Go** — the `go` directive in `go.mod` (`go 1.21`).

**asdf / mise** — `.tool-versions` (one `tool version` line per tool: `nodejs
20.11.0`, `python 3.12.1`, `golang 1.21`).

**CI matrices** — `.github/workflows/*.yml`: the versions a matrix tests against
(`node-version: [18, 20]`, `python-version: ['3.11', '3.12']`, `go-version`). A
trailing matrix entry is itself a pin of "what we still support."

**Containers** — the version tag in a `FROM` line of `Dockerfile*` and the
`image:` tags in `docker-compose*` (`FROM node:18`, `python:3.11-slim`). A tag
with no version (`FROM scratch`, `FROM ubuntu` with no tag, `:latest`) is **not** a
pin — there is no declared version to fall behind.

**Best-effort installers (lower confidence, recommend-only)** — grep `scripts/`,
`README*`, and `Makefile` for inline version mentions (`nvm install 18`, "requires
Node 18+", `PYTHON_VERSION=3.11`). These are **prose, not a declared pin file**:
the match may be stale documentation or an example, and there is no owned file to
mutate. Mark every such finding `low_confidence` — it surfaces as a
**recommendation only and is never auto-applied** (the apply gate enforces this;
see Apply).

Distinguish a **toolchain pin** (what this audit owns) from a **library
dependency version** (Dependabot's job — a pinned package in `package.json`
`dependencies`, `requirements.txt`, `go.mod`'s `require` block). Library deps are
**Deferred to Dependabot**; do not flag them here.

**Dependabot / Renovate presence.** As part of the scan, check whether the repo
configures automated library bumps: `.github/dependabot.yml` (or `.yaml`),
`renovate.json`, or `.renovaterc`. If **none** exists, flag the gap and recommend
setting one up — this audit covers toolchain pins, but library deps still need an
owner, and their absence is itself a staleness risk. Carry a **Deferred to
Dependabot** note in the report regardless: library dependency bumps are out of
this audit's scope by design.

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

**For an `impose` floor, the gap against `latest` is not the signal — two other
things are.** First, is the floor **past EOL**? A floor of `node >=16` once Node
16 is dead means the repo advertises support for a runtime that gets no security
fixes; that is a real recommendation (to *raise* the floor off the dead major).
Second, is the floor **higher than what the repo itself satisfies** — does it
require consumers to be *newer* than the repo's own `.nvmrc` / `.tool-versions` /
CI matrix? That is the bleeding-edge-on-others defect (a `devEngines:
pnpm ^11` no one can install, an `engines.node >=22` while the repo tests on 20):
the floor demands more of consumers than the project itself runs, with no reason.
Flag it as a recommendation to **lower** the floor to what the repo actually
supports. Both are recommend-only — neither is a mechanical bump (see Apply).

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

**Never auto-apply a floor.** A pin tagged `is_floor` at scan — `engines`,
`devEngines`, a `requires-python` lower bound, a peer-dependency range — is a
constraint the repo imposes on its **consumers**, not a version it runs on.
Raising it sheds consumers and lowering it is a support-policy judgment; either
way the local verify gate proves nothing about downstream impact. Pass
`is_floor=True` and `apply_policy.decide` returns `recommended: floor
(consumer-imposed)` and never `"apply"`, regardless of gap, EOL, ownership, or
verify result — decided right after `low_confidence`, because like it the floor is
distrusted by *shape* (the bump's direction), not by target.

**Never auto-apply a best-effort installer finding.** A pin grepped out of
`scripts/`, `README*`, or `Makefile` (marked `low_confidence` at scan) has no
reliable owned file to mutate — the match may be stale docs or an example. Pass
`low_confidence=True` and `apply_policy.decide` returns `recommended: low
confidence (installer)` and never `"apply"`, regardless of gap, EOL, ownership, or
verify result. This is the deterministic floor: source-distrust is decided ahead
of every other disposition, so model judgment can never promote a grep match into
an unattended mutation.

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
including any downgraded to `recommended (verify failed)`, any installer match as
`recommended: low confidence (installer)`, any floor as `recommended: floor
(consumer-imposed)` (and, for an over-constrained floor, say so in `migration`:
"lower to <what the repo runs>"), or, when no verify command was found, every
finding as `unverified: no verify command`.

Close the report with a **Deferred to Dependabot** note: library dependency bumps
are out of scope by design. If the scan found no Dependabot/Renovate config,
escalate the note to a flagged gap — name the missing config and recommend
standing one up, since the library deps it would own are otherwise unwatched.

### Register

The skill is registered in `.claude-plugin/plugin.json` and linked from the
top-level `README.md`, per repo convention (the `check-skill-registration` Stop
hook enforces it).

## Scope at this slice

- **The full v1 toolchain surface.** Node, Python, Go, asdf/mise `.tool-versions`,
  CI matrices, container `FROM` tags, plus best-effort installer hints — all on the
  same `scan` step, not separate skills. Library dependency versions stay out of
  scope (Deferred to Dependabot).
- **Auto-apply only the safe, verified bumps.** In-major (patch/minor) bumps on
  owned files are applied behind a verify gate, one at a time, with per-bump
  revert. Cross-major / EOL jumps, any unverified finding, any low-confidence
  installer finding, and any consumer-imposed floor (`engines`, `devEngines`,
  `requires-python` lower bound, peer ranges) are recommend-only — the apply
  station may only ever act on a *verified, satisfy-role* finding from a declared
  pin file that it can prove green.

## Anti-Patterns

- **Re-deriving the gap, the ranking, or the apply gate in prose.** All three are
  tested pure functions ([`version_gap.py`](lib/version_gap.py),
  [`rank.py`](lib/rank.py), [`apply_policy.py`](lib/apply_policy.py)); call them.
- **Guessing a version or EOL when web is down.** Degrade to `unverified: no web
  access` and suppress apply — never fabricate upstream data.
- **Auto-applying a cross-major, EOL, or installer-grepped finding.** Cross-major
  and EOL jumps carry breaking-change migration; an installer hint has no reliable
  owned file. All three are recommendations, never mechanical bumps — let
  `apply_policy.decide` gate it (`low_confidence` for installer matches).
- **Bumping a consumer-imposed floor toward latest.** `engines`, `devEngines`, a
  `requires-python` lower bound, and peer ranges are floors the repo imposes on
  others — raising one toward "latest" is not remediation, it sheds consumers. A
  floor is `is_floor` (recommend-only, both directions); its real signals are
  past-EOL and being *higher than what the repo itself runs* (the
  bleeding-edge-on-others defect — recommend lowering it).
- **Treating a non-version tag as a pin.** `FROM scratch`, an untagged image, or
  `:latest` declares no version to fall behind — skip it, don't flag a phantom gap.
- **Flagging a library dependency.** A package version in `dependencies` /
  `requirements.txt` / `go.mod`'s `require` block is Dependabot's job, not a
  toolchain pin — Deferred to Dependabot.
- **Bumping without a verify gate, or batching bumps.** No discoverable verify
  command means no apply at all. With one, apply a single bump per verify so a
  failure pins to the bump that caused it; keep on pass, revert on fail.
- **Hardcoding a file catalogue as the rule.** Pins are a concept; match the
  repo's real layout, with the common files as illustrative starting points
  (ADR 0002).
- **Overlapping Dependabot.** Library bumps are Dependabot's job; this audit is
  for the toolchain pins it does not touch.
