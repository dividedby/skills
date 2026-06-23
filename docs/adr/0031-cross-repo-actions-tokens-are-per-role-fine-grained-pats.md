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

Cross-repo GitHub Actions access uses **fine-grained PATs, one per role,
least-privilege, scoped to exactly the repos that role touches.** This codifies the
pattern already in force.

| Role | Token | Scope | Stored in |
| --- | --- | --- | --- |
| Tracker-write | `SKILLS_TRACKER_TOKEN` | Issues: read/write on `dividedby/skills` only | each active consumer repo (one copy each) |
| Cost-scrape | the per-target `*_ACTIONS_TOKEN` set — **kept split** | Actions: read, each scoped to one repo | hub: `dividedby/agent-research` only |
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

The five cost-scrape `*_ACTIONS_TOKEN` PATs are **deliberately not collapsed** into
one Actions:read PAT spanning every repo. They are least-privilege fan-in (each
reads exactly one repo's Actions logs), not accidental duplication. Collapsing them
would buy a one-time provisioning saving in exchange for a permanently wider blast
radius on the hub, and would contradict the "least privilege per channel"
principle. The only role with genuine N-way duplication is tracker-write, and that
is already "one logical token per role" — copied per repo only because a User
account offers no shared-secret mechanism.

## Security invariant

Each token carries the minimum permission for its role on the minimum set of repos,
with a finite expiry. A leak of any one token is bounded to that role on those
repos: a leaked `SKILLS_TRACKER_TOKEN` can spam issues on `dividedby/skills` and
nothing else; a leaked `*_ACTIONS_TOKEN` can read one repo's Actions logs and
nothing else. No single cross-repo token grants account-wide access.

## Consequences

- The estate's token model is now recorded; onboarding cites this ADR instead of
  re-deriving it. Structurally nothing changes — the decision ratifies what is
  already deployed.
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
- `docs/onboarding/consumer-setup.md`, `dividedby/agent-research docs/cost-tracking.md` — the existing per-channel prescriptions this ADR codifies
