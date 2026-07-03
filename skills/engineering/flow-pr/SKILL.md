---
name: flow-pr
description: >
  Flow-aware end-to-end PR helper — cuts a feature branch from the repo's
  default branch, commits → pushes → opens a PR with the default branch as
  base, reviews and fixes the diff (via `/review`), gates on CI, then merges
  to the default branch. When the default branch is not main, promotion
  (default→main) is a separate always-confirmed mode. Invokable as a slash
  command or by the model on a done+green signal.
---

# Flow PR

End-to-end PR lifecycle for a unit of work: default branch detection, branch
cutting, commit → push → PR open, review gate, CI gate, and merge. The policy
layer on top of existing mechanics.

Defers:
- **Commit message policy** → `/commit`
- **Code-review logic** → `/review` (flow-pr *runs* it as the review gate; does not implement it)
- **Issue filing** → repo's intake convention
- **Merge mechanics** → [`merge-mechanics.md`](merge-mechanics.md)

> `/review` here means the installed two-axis Standards+Spec skill (Matt's,
> pre-rename) — it's still what resolves locally today. Upstream renamed the
> skill `code-review` on 2026-07-01, which collides with the built-in
> `/code-review` command and the official code-review plugin; when the
> installed copy adopts the rename, update these refs. #529 owns the larger
> review-gate verdict.

---

## Default branch detection

The repo's **default branch is always the integration target**. Read it dynamically:

```
gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'
```

Examples:
- `main` (library/tool) → feature PRs merge to `main`; promotion doesn't apply.
- `staging` (deployed app) → feature PRs merge to `staging`; promotion (`staging → main`) is a separate always-confirmed step.

**Override (rare).** If a repo uses a non-default branch as its integration target, add to the repo's `CLAUDE.md`: `Flow-PR integration branch: <branch>`. The skill reads this before the API call and uses it instead.

---

## Feature mode (default path)

Runs when the user signals done/ship, or when all autonomy triggers below are satisfied.

1. **Branch check.** If already on a `feature/*` branch, stay on it. If on the default branch, cut a `feature/<slug>` branch from it first. Never commit directly onto the default branch.

2. **Commit → push.** Use `/commit` for commit message policy. Push the feature branch to origin.

3. **Open PR.** `gh pr create --base <default-branch>`. The base is always the dynamic default branch — never hardcode `main` if the default is `staging`.

   PR body format:

   ```
   ## Summary
   <1–3 bullets>

   ## Test plan
   [Bulleted checklist]

   🤖 Generated with [Claude Code](https://claude.ai/claude-code)
   ```

   If a PR for the branch already exists, update it instead of opening a new one. Check with `gh pr list --head <branch>` first (idempotent).

4. **Review gate (default on).** Invoke `/review` on the PR diff and apply fixes. Loop review → fix → re-review until `/review` reports no actionable findings or a **2-pass cap** is hit. If actionable findings remain at the cap, halt and surface them — do not merge.

   Skip only on explicit caller opt-out (`/flow-pr skip-review` or a stated "skip review"). Do not auto-classify the diff to decide — diff size and file type are poor proxies for review need.

5. **CI gate.** Poll `gh pr checks` until all checks pass. Do not merge with red or pending CI.

6. **Merge.** `gh pr merge --merge` (merge-commit only; see [`merge-mechanics.md`](merge-mechanics.md)).

7. **Post-merge sync.**
   - `git checkout <default-branch> && git pull`
   - `git branch -d <feature-branch>` (remote branch is auto-deleted by GitHub; local is not)

---

## Promotion mode

Applies only when the default branch is **not** `main`. When the default branch is `main`, feature merges are the final step and promotion doesn't exist.

Always user-confirmed before running.

- Triggered only by explicit invocation: `/flow-pr promote` or an explicit user request. Never auto-triggered.
- Opens `gh pr create --base main` from the default branch (e.g. `staging → main`).
- Merge-commit only; never squash or rebase.

---

## Autonomy triggers

**Fire when all hold:**
- User explicitly signals done/ship, OR a coherent unit of work is logically complete, AND
- The verify gate is green (tests, typecheck, CI), AND
- The working tree is a reviewable diff (not mid-edit noise).

**Do not fire:**
- After individual file edits.
- Mid-task or on work-in-progress.
- When the verify gate is red or failing.
- Before the unit is logically complete.
- On structural work without first proposing and getting go-ahead.

A passing verify gate is what makes autonomous merge trustworthy — it is not optional.

---

## GraphQL flap resilience

`gh pr create` and `gh pr merge` route through GraphQL, which can intermittently 401 even when auth is healthy.

- **`gh pr create` failure:** fall back to REST — `gh api -X POST repos/{owner}/{repo}/pulls -f title=... -f body=... -f head=... -f base=...`
- **`gh pr merge` failure:** fall back to local `git merge --no-ff <feature-branch>` + `git push` from the integration branch (GitHub marks the PR merged).
- Check `gh auth status` before assuming a real auth failure. Note: `gh auth status` can report healthy without live-validating the token.
- If REST also 401s after a GraphQL flap, it is a real auth issue — surface to the user, do not re-run.
