#!/usr/bin/env python3
"""PreToolUse Bash guard: hard-block destructive git during unattended runs.

The two proposal loops (apply-agent-research, improve-codebase-architecture)
carry a prose "no destructive git" invariant. In CI / unattended `claude -p`
the maintainer's global ~/.claude guards are absent, so that invariant rests
only on prompt discipline. This checked-in hook makes the block deterministic:
it inspects the candidate Bash command and exits 2 (with a stderr reason) for
destructive git, exits 0 for everything else. It stays git-scoped on purpose —
broader command guards (rm -rf, etc.) are a separate concern.

Normal loop operations (commit, push, add, status, checkout -b, branch switch)
pass through untouched.

Payload: the documented PreToolUse shape on stdin —
  {"tool_name": "Bash", "tool_input": {"command": "..."}}
"""
import json
import os
import re
import sys

# Each entry: (compiled pattern, label explaining the refusal). Matched
# case-insensitively against the full command text. `[^|;&\n]*` keeps a match
# within a single command segment so flags from a later piped command don't
# leak in. To extend the guard, add a pattern here with an intent label.
PATTERNS = [
    # force push rewrites shared history; --force-with-lease is the safe form
    (re.compile(r'\bgit\s+push\b[^|;&\n]*(?:--force(?!-with-lease)\b'
                r'|(?:^|\s)-[a-z]*f[a-z]*(?=\s|$))', re.IGNORECASE),
     'git force-push (rewrites shared history; use --force-with-lease)'),
    # hard reset discards the working tree and index
    (re.compile(r'\bgit\s+reset\b[^|;&\n]*--hard\b', re.IGNORECASE),
     'git reset --hard (discards working tree + index)'),
    # force clean deletes untracked files; -n/--dry-run is harmless and ignored
    (re.compile(r'\bgit\s+clean\b[^|;&\n]*(?:--force\b'
                r'|(?:^|\s)-[a-z]*f[a-z]*(?=\s|$))', re.IGNORECASE),
     'git clean -f (deletes untracked files)'),
    # checkout that discards working-tree changes: --force/-f, a `--` pathspec,
    # or a bare `.`  (plain `git checkout <branch>` / `-b <new>` is allowed)
    (re.compile(r'\bgit\s+checkout\b[^|;&\n]*(?:--force\b'
                r'|(?:^|\s)-[a-z]*f[a-z]*(?=\s|$)'
                r'|\s--(?:\s|$)'
                r'|\s\.(?=\s|$))', re.IGNORECASE),
     'git checkout that discards working-tree changes'),
]

# Patterns enforced only in unattended runs (CI / `claude -p`). Branch deletion
# drops a local ref but never touches the working tree or shared history, so
# interactively — where the maintainer is present to catch mistakes — it is a
# routine cleanup. Unattended, the maintainer's global guards are absent, so it
# stays blocked. See is_unattended().
UNATTENDED_ONLY_PATTERNS = [
    (re.compile(r'\bgit\s+branch\b[^|;&\n]*(?:--delete\b'
                r'|(?:^|\s)-[a-z]*[dD][a-z]*(?=\s|$))', re.IGNORECASE),
     'git branch delete (drops a local branch ref)'),
]


def is_unattended() -> bool:
    """True in CI / unattended `claude -p`, false in an interactive session.

    GitHub Actions always sets CI=true and GITHUB_ACTIONS=true; neither is
    present in a local interactive shell. These are the repo's unattended
    contexts (the two proposal-loop workflows).
    """
    return bool(os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'))

# git restore touches the worktree by default. Block it unless it is a
# pure --staged unstage (no --worktree / -W), which leaves the worktree intact.
_GIT_RESTORE = re.compile(r'\bgit\s+restore\b([^|;&\n]*)', re.IGNORECASE)
_RESTORE_WORKTREE = re.compile(r'(?:--worktree\b|(?:^|\s)-[a-z]*W[a-z]*(?=\s|$))')
_RESTORE_STAGED = re.compile(r'--staged\b|(?:^|\s)-[a-z]*S[a-z]*(?=\s|$)')


def restore_is_destructive(args: str) -> bool:
    if _RESTORE_WORKTREE.search(args):
        return True
    # --staged alone only unstages; without it, restore defaults to the worktree
    return not _RESTORE_STAGED.search(args)


def find_block(cmd: str):
    for pat, label in PATTERNS:
        if pat.search(cmd):
            return label
    m = _GIT_RESTORE.search(cmd)
    if m and restore_is_destructive(m.group(1)):
        return 'git restore that discards working-tree changes'
    if is_unattended():
        for pat, label in UNATTENDED_ONLY_PATTERNS:
            if pat.search(cmd):
                return label
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = ((data.get('tool_input') or {}).get('command') or '')
    if not cmd:
        return 0
    label = find_block(cmd)
    if label:
        print(f'Blocked by project git-guard: {label}. This is disallowed in '
              f'unattended runs; ask the user before running it.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
