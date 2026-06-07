# Stop-Hook Test Gate for lib/ Python Changes

This repo will **not** add a conditional test-suite invocation to the Stop hook
that runs the Python unit suite when `lib/` (or harness/skill core) Python files
change this turn. The underlying discipline — fail breakage early, with a binary
gate rather than an advisory signal — is sound; it is just already delivered by CI
for this repo's shape.

## Why this is out of scope

The lib/harness unit suites are **already gated**, deterministically, on every
push and PR:

- `apply-agent-research-lib-tests.yml` — path-filtered gate on the
  apply-agent-research lib suite.
- `harness-tests.yml` — the de-vendored proposal-loop harness (`harness/cli.py`,
  21 stdlib tests).
- `hook-self-tests.yml` — the hooks' own self-tests
  (`check-skill-registration`, `git-guard`).

The proposal's only delta over these is **when** the signal surfaces: turn-end
(Stop hook) vs. post-push (CI). For a single-maintainer repo where the agent
opens a PR for review anyway, the post-push gate already blocks the merge, and the
turn-end gate buys little — while adding a per-turn cost (running the suite on
every Stop that touched Python) and a second place the same gate logic must be
maintained and kept in sync with the CI path-filters.

The knowledge note (mariozechner/commit-hook-checks-over-lsp-diagnostics) argues
binary gates over advisory LSP-style signals. CI **is** the binary gate here: it
is non-advisory and blocks the merge. The note's failure mode — *no* enforcing
gate, only advisory diagnostics — does not apply; the enforcing gate exists.

## If this is ever reconsidered

The bar to revisit is a demonstrated gap CI does *not* close — e.g. an agent
loop that commits and **merges** lib/ breakage without a PR gate (a true
turn-end-only workflow with no CI between commit and effect), where the only place
to catch it is before the turn clears. That would argue for a turn-end gate; the
current PR-gated flow does not.

## Prior requests

- #124 — "Add conditional test gate to Stop hook for lib/ Python changes"
  (`source:agent-research`; source:
  mariozechner/commit-hook-checks-over-lsp-diagnostics).
