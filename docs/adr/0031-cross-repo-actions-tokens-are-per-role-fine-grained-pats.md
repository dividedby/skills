# Cross-repo Actions tokens are per-role least-privilege fine-grained PATs

## Context

The fleet runs several cross-repo GitHub Actions credentials: consumer loops file
`skill-request`/`skill-promotion` issues into `dividedby/skills`, the cost hub in
`dividedby/agent-research` scrapes each repo's Actions logs for `total_cost_usd`,
and the drift detectors in `dividedby/skills` read each consumer's vendored
workflow and label files. Spike #424 asked whether to consolidate these tokens and
which mechanism to standardize on (classic PAT, fine-grained PAT, org-level Actions
secret, or a GitHub App).

Two facts constrain the answer:

1. **`dividedby` is a User account, not an Organization** (`gh api users/dividedby
   -q .type` → `User`). Organization-level Actions secrets do not exist on a User
   account. "Share one stored secret across N repos" is therefore unavailable by
   any mechanism: on a User account a credential is always pasted into each repo
   individually. "Consolidation" here can only mean *fewer distinct token
   identities*, never *one secret reachable by many repos*.
2. **The estate already runs fine-grained, least-privilege, per-channel PATs** and
   documents that intent (`docs/onboarding/consumer-setup.md`,
   `dividedby/agent-research docs/cost-tracking.md`), but no ADR had recorded it as
   a decision, so onboarding kept re-litigating the token model.

The actual GitHub-PAT estate is three roles. Everything else in the secret
inventory is out of scope: `GITHUB_TOKEN` (auto-minted per run),
`CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_API_KEY` (model auth, not GitHub tokens),
`VPS_*` / `EGRESS_*` (infra SSH/config), and `MIRROR_DEPLOY_KEY` (an SSH deploy
key) are not cross-repo GitHub PATs and are not governed by this decision.

## Decision

Cross-repo GitHub Actions access uses **fine-grained PATs, one per role.**
Tracker-write and drift-read stay scoped to exactly the repos they touch; the
cost-scrape role uses a **single token scoped to all repositories, current and
future** (a maintainer decision — see below).

| Role | Token | Scope | Stored in |
| --- | --- | --- | --- |
| Tracker-write | `SKILLS_TRACKER_TOKEN` | Issues: read/write on `dividedby/skills` only | each active consumer repo (one copy each) |
| Cost-scrape | a single `ACTIONS_TOKEN` | Actions: read on **all repositories (current and future)** | hub: `dividedby/agent-research` only |
| Drift-read | `DRIFT_CHECK_TOKEN` | Contents: read on the active consumer repos | `dividedby/skills` only |

Rejected alternatives:

- **Classic PAT** — a security regression. Classic PATs grant every repo the user
  can access (the whole account, including private repos beyond the fleet) under
  coarse scopes. It also saves no real effort on a User account: a classic PAT is
  still pasted per repo. Rejected.
- **Org-level Actions secret** — unavailable. `dividedby` is a User account, not an
  Organization. Off the table without an account-structure migration far outside
  this decision.
- **GitHub App** — the most secure option, and that is why it loses here. Hourly
  auto-minted ephemeral tokens are marginal security bought with a recurring
  complexity tax: registering an App, custody of its private key, and a
  token-minting step in every workflow. For a five-repo personal estate where the
  maintainer has explicitly preferred simplicity over marginal security, this is
  over-engineering. Rejected.

**Maintainer decision — cost-scrape uses one all-repos token.** The cost-scrape role
uses a single `ACTIONS_TOKEN`: a fine-grained PAT with **Actions:read on all
repositories** the account owns. A fine-grained PAT scoped to "all repositories"
automatically includes repos created later, so a new repo's cost scrape works with
no new secret — zero-touch onboarding. This **overrides the #424 audit's
recommendation to keep five per-repo tokens.** The trade is deliberate: per-repo
least-privilege is given up for operational simplicity — one secret to provision and
rotate, future repos covered automatically. The accepted blast radius stays narrow
because the permission is **Actions:read only** (log/artifact reads — no write, no
contents, no issues), which is why the maintainer judges the wider repo scope
acceptable. The five `SKILLS_ACTIONS_TOKEN` / `GOODREADS_ACTIONS_TOKEN` /
`MOODREADER_ACTIONS_TOKEN` / `TWEAKCC_ACTIONS_TOKEN` / `CLAUDE_CONFIG_ACTIONS_TOKEN`
secrets are retired in favor of the single `ACTIONS_TOKEN`.

Tracker-write keeps its tight scope because `Issues:write` is a mutation grant, and
drift-read keeps Contents:read on the named consumers; neither was part of this
consolidation. The same all-repos simplification could later be applied to
drift-read if the maintainer wants it.

## Security invariant

Each token carries the minimum permission for its role, with a finite expiry. A leak
is bounded by permission, and for tracker-write and drift-read also by repo: a leaked
`SKILLS_TRACKER_TOKEN` can only spam issues on `dividedby/skills`; a leaked
`DRIFT_CHECK_TOKEN` can only read consumer repo contents. The consolidated
`ACTIONS_TOKEN` is Actions:read across all repositories — a leak exposes Actions
log/artifact reads account-wide, but **no write, no contents, and no issues access**.
No cross-repo token grants write or account-wide mutation.

## Consequences

- The token model is recorded; onboarding cites this ADR instead of re-deriving it.
  Tracker-write and drift-read ratify the deployed state; cost-scrape consolidates
  from five per-repo tokens to one all-repos `ACTIONS_TOKEN`.
- New repos are covered automatically for cost-scrape: the `ACTIONS_TOKEN`
  (fine-grained, "all repositories") picks up future repos with no new secret — only
  the hub's cost-ledger workflow needs a scrape entry for the new repo.
- Migrating to the single token touches the hub only: `dividedby/agent-research`
  `cost-ledger.yml` and `docs/cost-tracking.md` / `COST_SURFACE` switch from the five
  `*_ACTIONS_TOKEN` names to `ACTIONS_TOKEN`. Provisioning `ACTIONS_TOKEN` and
  retiring the five old secrets are admin steps.
- Provisioning, granting, and rotating tokens are admin operations on a User
  account and remain **maintainer-only** (human checkpoints); no autonomous agent
  provisions, writes, or rotates secrets.
- Any rotation follows add-new → verify-green → retire-old across all holding repos,
  so no running loop is left credential-less mid-rotation.
- Out-of-scope credentials (model auth, infra SSH, deploy keys) are unaffected by
  this decision.
- If the fleet ever outgrows a User account and moves to an Organization,
  org-level secrets become available and this decision should be revisited for the
  tracker-write role specifically (the only one copied per repo today).

## References

- Issue #424 — the consolidation spike and its audit
- [ADR 0014](0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md) — fetch-fresh pattern
- [ADR 0015](0015-apply-agent-research-prompt-is-consumer-portable-via-env.md) — env-wiring portability; `SKILLS_TRACKER_TOKEN` as the host/consumer role discriminator
- [ADR 0030](0030-cross-repo-credential-selected-inside-cli-py.md) — where the tracker-write token is selected (inside `cli.py`, allowlist-safe)
- `docs/onboarding/consumer-setup.md`, `dividedby/agent-research docs/cost-tracking.md` — the existing per-channel prescriptions (codified here for tracker-write and drift-read; superseded for cost-scrape, which consolidates to one all-repos token)
