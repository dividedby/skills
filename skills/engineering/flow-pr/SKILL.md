---
name: flow-pr
description: >
  Flow-aware end-to-end PR helper — cuts a feature branch from the repo's
  default branch, commits → pushes → opens a PR with the default branch as
  base, gates on CI, then merges to the default branch. When the default
  branch is not main, promotion (default→main) is a separate always-confirmed
  mode. Invokable as a slash command or by the model on a done+green signal.
---

# Flow PR

This skill owns the **end-to-end PR lifecycle** for a unit of work: default
branch detection, branch cutting, commit → push → PR open, CI gate, and merge
to the default branch. It is the policy layer on top of existing mechanics.

What it defers:

- **Commit message policy** → defer to `/commit`.
- **Code review** → defer to `/review`.
- **Issue filing** → defer to the repo's intake convention.
- **Merge mechanics detail** → `~/.claude/branching-flow.md` is the
  authoritative source; this skill references it, never duplicates it.

---

## Default branch detection

The repo's **default branch is always the integration target** — the safe
merge destination for feature work. Read it dynamically:

```
gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'
```

No role classification needed. Examples:
- `main` (lib/tool) → feature PRs merge to `main`; promotion doesn't apply.
- `staging` (deployed app) → feature PRs merge to `staging`; promotion
  (`staging → main`) is a separate always-confirmed step.

**Override (rare).** If a repo uses a non-default branch as its integration
target (unusual), add a one-liner to the repo's `CLAUDE.md`:
`Flow-PR integration branch: <branch>`. The skill reads this before the API
call and uses it instead.

---

## Feature mode (default path)

Runs when the user signals done/ship, or when the autonomy triggers below
are satisfied.

1. **Branch check.** If already on a `feature/*` branch, stay on it. If on
   the default branch, cut a `feature/<slug>` branch from it first. Never
   commit directly onto the default branch.

2. **Commit → push.** Use `/commit` for commit message policy. Push the
   feature branch to origin.

3. **Open PR.** `gh pr create --base <default-branch>`. The base is always the
   default branch — never hardcode `main` if the default is `staging`.
   PR body uses the standard format:

   ```
   ## Summary
   <1–3 bullets>

   ## Test plan
   [Bulleted checklist]

   🤖 Generated with [Claude Code](https://claude.ai/claude-code)
   ```

   If a PR for the branch already exists, update it instead of opening a new
   one (idempotent — check with `gh pr list --head <branch>` first).

4. **Gate on CI.** Poll `gh pr checks` until all checks pass. Do not merge
   with red or pending CI.

5. **Merge.** `gh pr merge --merge` (merge-commit only; see Constraints).

6. **Post-merge sync.** After a successful merge:
   - `git checkout <default-branch> && git pull` — bring local default branch
     up to date with the merge commit.
   - `git branch -d <feature-branch>` — delete the local feature branch.
     (The remote branch is auto-deleted by GitHub's auto-delete-on-merge
     setting; the local branch is not.)

---

## Promotion mode

Applies only when the default branch is **not** `main` (e.g. `staging`). When
the default branch is `main`, promotion doesn't exist — feature merges ARE the
final step.

Separate from feature mode and **always user-confirmed** before running.

- Triggered only by explicit invocation: `/flow-pr promote` or an explicit
  user request. Never auto-triggered.
- Opens a promotion PR: `gh pr create --base main` from the default branch
  (e.g. `staging → main`).
- Always ask the user before executing — do not infer that "ship it" means
  promote to `main`.
- Merge commit only; never squash.

---

## Autonomy and trigger semantics

**Fire when all hold:**
- User explicitly signals done/ship, OR
- A coherent unit of work is logically complete AND
- The verify gate is green (tests, typecheck, CI) AND
- The working tree is a reviewable diff (not mid-edit noise).

**Do NOT fire:**
- After individual file edits.
- Mid-task or on work-in-progress.
- When the verify gate is red or failing.
- Before the unit is logically complete.
- On structural work without first proposing and getting go-ahead (honors the
  "discuss before non-trivial" rule).

The green verify gate is the primary self-exclusion mechanism for partial or
broken states. A passing gate is not optional — it is what makes autonomous
merge trustworthy.

---

## GraphQL flap resilience

`gh pr create` and `gh pr merge` route through GraphQL, which can
intermittently 401 even when auth is healthy.

- On `gh pr create` failure: fall back to REST —
  `gh api -X POST repos/{owner}/{repo}/pulls -f title=... -f body=... -f head=... -f base=...`
- On `gh pr merge` failure: fall back to local
  `git merge --no-ff <feature-branch>` + `git push` from the integration
  branch (GitHub marks the PR merged).
- Check `gh auth status` before assuming a real auth failure. Note:
  `gh auth status` can report healthy without live-validating the token.
- A GraphQL flap leaves REST working; if REST also 401s, it is a real auth
  issue — do not re-run; surface to the user.

---

## Constraints

- **Merge-commit only.** Never `--squash` or `--rebase`. Policy enforced at
  repo level; this skill enforces it at invocation time too.
- **Never direct-push** to the default branch.
- **Never merge red CI.** Poll and wait; halt if checks do not pass.
- **Never auto-promote to `main`.** Promotion is always an explicit,
  user-confirmed action.
- **Policy reference:** `~/.claude/branching-flow.md` is the source of truth
  for merge mechanics. This skill does not restate that policy — it enforces it.
