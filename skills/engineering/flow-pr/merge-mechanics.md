# Merge Mechanics

Universal merge policy for all repos using this skill.

## Merge-commit only

Always `gh pr merge --merge`. Never `--squash` or `--rebase`.

Squash and rebase rewrite SHAs, which breaks the merge-commit promotion model: a squashed branch reads as "unmerged" against its own PR, and SHA divergence makes staging↔main promotion unreliable.

## CI green before merge

Poll `gh pr checks` until all checks pass. Do not merge with red or pending CI.

Branch protection is not always enforced at the repo level, so CI is advisory — the skill enforces it at invocation time.

## Auto-delete on merge

Set `delete_branch_on_merge: true` at the repo level. Merged PR branches are cleaned up automatically by GitHub. Local branches are not — delete them manually with `git branch -d <feature-branch>` after pulling the updated default branch.

## Applying to a new repo

```
gh api -X PATCH repos/<owner>/<repo> \
  -F allow_squash_merge=false \
  -F allow_rebase_merge=false \
  -F allow_merge_commit=true \
  -F delete_branch_on_merge=true
```
