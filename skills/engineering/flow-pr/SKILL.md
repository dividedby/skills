---
name: flow-pr
description: >
  Flow-aware end-to-end PR helper — detects repo role, cuts a feature branch
  from the integration branch, commits → pushes → opens a PR, gates on CI,
  then merges to the integration branch. Promotion (staging→main) is a
  separate always-confirmed mode. Invokable as a slash command or by the
  model on a done+green signal.
---

# Flow PR

This skill owns the **end-to-end PR lifecycle** for a unit of work: role
detection, branch cutting, commit → push → PR open, CI gate, and merge to the
integration branch. It is the policy layer on top of existing mechanics.

What it defers:

- **Commit message policy** → defer to `/commit`.
- **Code review** → defer to `/pr-review`.
- **Issue filing** → defer to the repo's intake convention.
- **Merge mechanics detail** → `~/.claude/branching-flow.md` is the
  authoritative source; this skill references it, never duplicates it.

---

## Role detection

Three-step priority chain — stop at the first match:

### 1. Declared marker (authoritative)

Read the repo's `CLAUDE.md` for a 1–2 line role marker:

- **deployed-app**: `Role: deployed-app · integration branch: staging (mechanics: ~/.claude/branching-flow.md)`
- **lib/tool (trunk)**: `Role: trunk · integration branch: main (mechanics: ~/.claude/branching-flow.md)`

If the marker is present, use it. Do not re-infer.

### 2. Inference fallback (un-onboarded repo)

Check default branch and branch existence:

- A non-`main` integration branch (`staging`, `develop`, `integration`), or a `staging` branch plus a deploy workflow keyed to staging/main → **deployed-app**.
- Plain `main`/`master` with no staging branch → **trunk/lib**.

### 3. Ambiguous → confirm + write marker

If inference is ambiguous, confirm the inferred role with the user. Once
confirmed, write the marker to `CLAUDE.md` (see Per-repo marker bootstrap
below) so the role is declared from then on.

---

## Per-repo marker bootstrap

On first run against an un-onboarded repo, write a thin marker into the repo's
`CLAUDE.md`. Never copy the full policy — only the one-liner role + pointer:

```
Role: deployed-app · integration branch: staging (mechanics: ~/.claude/branching-flow.md)
```

or

```
Role: trunk · integration branch: main (mechanics: ~/.claude/branching-flow.md)
```

This keeps each repo's `CLAUDE.md` minimal while making every subsequent
invocation authoritative (step 1 of role detection).

---

## Feature mode (default path)

Runs when the user signals done/ship, or when the autonomy triggers below
are satisfied.

1. **Branch check.** If already on a `feature/*` branch, stay on it. If on
   the integration branch (`staging` or `main`), cut a `feature/<slug>` branch
   from it first. Never commit directly onto the integration branch.

2. **Commit → push.** Use `/commit` for commit message policy. Push the
   feature branch to origin.

3. **Open PR.** `gh pr create --base <integration-branch>`. For deployed-app
   repos the base is `staging`, never `main`. PR body uses the standard format:

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
   GitHub auto-deletes the branch if the repo has auto-delete enabled.

---

## Promotion mode

Separate from feature mode and **always user-confirmed** before running.

- Triggered only by explicit invocation: `/flow-pr promote` or an explicit
  user request. Never auto-triggered.
- Opens a promotion PR: `gh pr create --base main` from the integration branch
  (e.g. `staging → main`).
- Always ask the user before executing — do not infer that "ship it" means
  promote to main.
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
- **Never direct-push** to the integration branch or default branch.
- **Never merge red CI.** Poll and wait; halt if checks do not pass.
- **Never auto-promote to `main`.** Promotion is always an explicit,
  user-confirmed action.
- **Policy reference:** `~/.claude/branching-flow.md` is the source of truth
  for merge mechanics. This skill does not restate that policy — it enforces it.
