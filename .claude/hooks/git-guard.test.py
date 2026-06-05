#!/usr/bin/env python3
"""Self-test for git-guard.py.

Runs the hook as a subprocess with a synthetic PreToolUse payload on stdin and
asserts exit 2 (blocked) for destructive git and exit 0 (allowed) for benign
commands and non-git commands. This test is the feedback gate for the guard:
run it directly (`./git-guard.test.py`) — no test framework required.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).with_name("git-guard.py")

# (command, should_be_blocked)
BLOCK = True
ALLOW = False

# Always-enforced cases. Run with the unattended signal cleared (interactive)
# to prove these block regardless of environment. Branch deletion is tested
# separately below since it is environment-sensitive.
CASES = [
    # force push (shared-history rewrite) — but --force-with-lease is allowed
    ("git push --force", BLOCK),
    ("git push -f", BLOCK),
    ("git push --force origin main", BLOCK),
    ("git push origin main --force", BLOCK),
    ("git push -fu origin main", BLOCK),
    # hard reset (discards working tree + index)
    ("git reset --hard", BLOCK),
    ("git reset --hard HEAD~1", BLOCK),
    # force clean (deletes untracked files)
    ("git clean -f", BLOCK),
    ("git clean -fd", BLOCK),
    ("git clean -xfd", BLOCK),
    # discard-style checkout / restore
    ("git checkout -- file.txt", BLOCK),
    ("git checkout .", BLOCK),
    ("git checkout --force", BLOCK),
    ("git checkout -f main", BLOCK),
    ("git restore file.txt", BLOCK),
    ("git restore .", BLOCK),
    ("git restore --worktree --staged file.txt", BLOCK),

    # benign git — the loop's own normal operations must pass
    ("git commit -m 'msg'", ALLOW),
    ("git push", ALLOW),
    ("git push origin main", ALLOW),
    ("git push --force-with-lease", ALLOW),
    ("git add .", ALLOW),
    ("git add -A", ALLOW),
    ("git status", ALLOW),
    ("git checkout -b new-branch", ALLOW),
    ("git checkout main", ALLOW),
    ("git switch main", ALLOW),
    ("git log --oneline", ALLOW),
    ("git diff", ALLOW),
    ("git fetch origin", ALLOW),
    ("git reset HEAD~1", ALLOW),          # soft/mixed reset keeps the worktree
    ("git restore --staged file.txt", ALLOW),  # only unstages
    ("git clean -n", ALLOW),              # dry run
    # non-git commands always pass
    ("npm test", ALLOW),
    ("ls -la", ALLOW),
    ("python3 build.py", ALLOW),
]

# Branch deletion is unattended-only: blocked in CI / `claude -p`, allowed in an
# interactive session where the maintainer can catch mistakes.
BRANCH_DELETE_CASES = [
    "git branch -D feature",
    "git branch -d feature",
    "git branch --delete feature",
]

# Signal that is_unattended() keys off of (GitHub Actions sets both).
UNATTENDED_ENV = {"CI": "true", "GITHUB_ACTIONS": "true"}


def run(cmd: str, unattended: bool) -> int:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    env = {k: v for k, v in os.environ.items() if k not in UNATTENDED_ENV}
    if unattended:
        env.update(UNATTENDED_ENV)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload, capture_output=True, text=True, env=env,
    )
    return proc.returncode


def main() -> int:
    failures = []

    def check(cmd, should_block, unattended):
        code = run(cmd, unattended)
        blocked = code == 2
        if blocked != should_block:
            want = "BLOCK" if should_block else "ALLOW"
            got = "BLOCK" if blocked else f"ALLOW(exit {code})"
            ctx = "unattended" if unattended else "interactive"
            failures.append(f"  [{ctx}] {cmd!r}: want {want}, got {got}")

    # Always-enforced cases: assert they hold even interactively (env cleared).
    for cmd, should_block in CASES:
        check(cmd, should_block, unattended=False)

    # Branch deletion flips on the unattended signal.
    for cmd in BRANCH_DELETE_CASES:
        check(cmd, BLOCK, unattended=True)
        check(cmd, ALLOW, unattended=False)

    if failures:
        print("git-guard self-test FAILED:\n" + "\n".join(failures))
        return 1
    total = len(CASES) + 2 * len(BRANCH_DELETE_CASES)
    print(f"git-guard self-test passed ({total} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
