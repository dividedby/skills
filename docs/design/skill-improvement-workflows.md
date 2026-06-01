---
feature: skill-improvement-workflows
status: superseded
superseded-by: cross-repo-knowledge-application
parent: "#14"
---

> **Superseded** by [`cross-repo-knowledge-application.md`](./cross-repo-knowledge-application.md)
> (agent-research ADR 0019, decentralized pull). The central-push run-books below
> were built but never wired; consumption is now a published `apply-agent-research`
> skill each consumer runs on itself. The pure helpers (`proposal_gate`,
> `sanitizer`) carry over; the rest is deprecated. Kept for history.
>
> **`runbooks/` is now retired** — the surviving helpers + the `cli.py` seam moved
> under the skill at `skills/meta/apply-agent-research/lib/` (ADR 0004 amendment).
> Any `runbooks/lib/...` path below is historical; read it at the new location.

# Design Plan: skill-improvement AFK workflows (C & D)

Implementation scaffolding for PRD #14. The issue tracker is authoritative for
issue bodies; this plan records modules, seams, invariants, and the testing
strategy. See ADR
[0003](../adr/0003-skill-improvement-workflows-propose-via-issues.md) for the
producer/decider model and `CONTEXT.md` for `run-book` and `integration map`.

## Load-bearing decision: the purity boundary

The **proposal gate** and **sanitizer guard** are **pure decision functions** —
inputs in, decision out. All tracker, git, and clone I/O is owned by the
run-books and injected. The tested logic never touches transport. This is the
seam that makes the ≤1/run cap, dedup, and the no-private-code rule testable
without the live tracker.

## Modules

- **Proposal gate** — pure. One reason to change: how a run selects/dedups its
  single proposal. Interface: `decide(candidates, openIssues) → {file: candidate
  | none}`. Invariants: never returns more than one; dedup is exact-key, not
  fuzzy; deterministic tie-break. Must not depend on the tracker. Shared by both
  run-books.
- **Sanitizer guard** — pure. One reason to change: what counts as leaked
  private content. Interface: `check(body) → allow | block(reason)`. Must not
  depend on the tracker. Used by both run-books — each reads a private source
  (the KB / the curated repos) and files into this public tracker (#26).
- **Self-improvement run-book** — orchestrator. Reads the KB + this repo,
  builds/commits the integration map, diffs it to surface refinements, calls the
  sanitizer guard then the proposal gate, files ≤1 `self-improvement` issue.
  Never edits skills directly.
- **Gap-scanner run-book** — orchestrator. Reads the curated repo-list, scans
  read-only with cleanup, detects recurring needs, calls the sanitizer guard
  then the proposal gate, files ≤1 generalized proposal.

## Seams

- **Tracker** — list-open-issues-by-label, create-issue. Owned by the run-books;
  pure modules never touch it. Fake: in-memory issue set (records created,
  serves open).
- **Repo-scan** (gap-scanner) — shallow clone + cleanup. Fake: local fixture
  directories.
- **KB-source** (self-improvement) — the acquisition contract C reads: a curated
  `kb-source.json` (KB slug + explicit `knowledge/` subpaths; no auto-discovery)
  + a reader over only those subpaths, feeding the injected `kb_reader`. The
  reader carries each note's `subject`/`category` axes — the two the integration
  map is built on (`skill ↔ practice/artifact`) — so consumers never re-parse the
  path. The C parallel to Repo-scan (#29). Fake: a `knowledge/`-shaped fixture
  tree. The KB root (clone transport) stays injected/out-of-scope (ADR 0003).
- **Map store** (self-improvement) — read/write + commit the integration map.
  Fake: a scratch path.

## Invariants

- At most one issue filed per run, per workflow (enforced by the gate).
- The VPS auto-commits analysis (the integration map) only; skill changes are
  always proposed as issues, never merged (ADR 0003).
- Both run-books' filed issues are generalized — no private content (enforced by
  the sanitizer guard on `title + body`; this repo's tracker is public). #26
  extended the guard from the gap-scanner to self-improvement, which also reads a
  private source (the KB).
- The integration map lives consumer-side; agent-research never depends on this
  repo.

## Testing strategy

- **Proposal gate (#15), Sanitizer guard (#18):** pure unit tests on synthetic
  inputs. Entry = the decision function. No fakes. Assert only the decision,
  never how inputs were gathered.
- **Run-books (#16, #17, #19, #20):** integration dry-runs against a faked
  tracker + fixture repos, wiring the *real* gate and sanitizer. Assert ≤1
  filed, dedup respected, map committed, working area empty after scan, filed
  body passes the real sanitizer. Prompt internals are not unit-tested.

## Issue index

- #15 — Proposal gate helper (pure) + tests
- #16 — Self-improvement run-book: build/auto-maintain the integration map
- #17 — Gap-scanner run-book: curated repo-list + read-only scan skeleton
- #18 — Sanitizer guard (pure) + tests
- #19 — Self-improvement run-book: file a real refinement (≤1/run)
- #20 — Gap-scanner run-book: file a real proposal (≤1/run, sanitized)
- #29 — Self-improvement run-book: pin the KB ingest contract (`kb-source.json`
  + reader), the C parallel to D's repo allow-list

All indexed issues are merged: both run-books, the shared pure helpers (gate,
sanitizer), and both acquisition contracts are built and tested. What remains is
**ops, intentionally out-of-scope here**: the VPS transport that runs them (deploy
key + `git clone` of the KB / curated repos, cron wiring) per ADR 0003, and
Twitter ingestion on the agent-research side (deferred until that data exists).

## Operational notes (for #16–#20)

**Provenance labels.** Each run-book tags its filed issue with a `source:`
label it also reads to dedup. Follow the convention the architecture-review
workflow already uses (`source:architecture-review`):

- C (self-improvement) → `source:self-improvement`
- D (gap-scanner) → `source:gap-scanner`

Create the label on first use, idempotently, the way the arch-review workflow
does (`gh label create … || true`). These are **provenance** labels, distinct
from the triage roles in `docs/agents/triage-labels.md` — the triage labels
still gate the human merge. (This resolves ADR 0003's placeholder "e.g.
`self-improvement`" to the `source:`-prefixed form for consistency.)

**Runner (resolved).** Both run-books run on the maintainer's existing
always-on VPS — the assumption in ADR 0003, now confirmed as real infra, not
aspirational. The VPS is the shared home: C reads the `agent-research` KB and
commits the integration map; D clones the curated private repos read-only. The
VPS authenticates with a deploy key / PAT (standard `git clone`); OpenVPN egress
is **not** a requirement (the maintainer is not routing-sensitive). The public
GitHub Actions path is rejected for D specifically because it would put a
private-repo read token in a public repo's Actions. Provisioning/cron wiring
remains an ops concern, out of scope for the issues.

**Sanitizer stays strict, structural-first.** The maintainer's private repos are
"personal, not for the world" rather than confidential — so the
`private_markers` list is *secondary*. The real risk is a stray secret
(`.env`, key, customer record) in a personal repo, so the load-bearing guard is
the **structural** one: never let raw repo content (fenced code, file paths,
import lines) into a public issue. Keep `check()` strict on pasted content even
though the repos themselves are not secrets.
