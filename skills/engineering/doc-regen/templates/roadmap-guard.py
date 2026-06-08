#!/usr/bin/env python3
"""PreToolUse roadmap self-update guard (TEMPLATE — copy to a consumer's
`.claude/hooks/` and edit the config block). Denies an issue-referencing
`git commit` unless ROADMAP is touched somewhere in the branch (staged, or
earlier vs the base branch). Fails open on anything it cannot determine.
Stdlib only (ADR 0004)."""
import json
import re
import subprocess
import sys

# --- config (edit per repo) -------------------------------------------------
ROADMAP = "docs/plans/roadmap.md"  # where the roadmap lives
BASE_BRANCH = "main"               # branch the PR merges into
# ---------------------------------------------------------------------------
ISSUE_REF = re.compile(r"#\d+")


def _changed() -> set[str]:
    files: set[str] = set()
    for args in (["git", "diff", "--cached", "--name-only"],
                 ["git", "diff", "--name-only", f"{BASE_BRANCH}...HEAD"]):
        try:
            out = subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)
        except Exception:
            continue
        files.update(line.strip() for line in out.splitlines() if line.strip())
    return files


def main() -> int:
    try:
        cmd = (json.load(sys.stdin).get("tool_input", {}) or {}).get("command", "")
    except Exception:
        return 0
    # Only enforce when the inline commit message references an issue.
    if "git commit" not in cmd or not ISSUE_REF.search(cmd):
        return 0
    if ROADMAP in _changed():
        return 0
    print(f"roadmap-guard: this commit references an issue but does not touch "
          f"{ROADMAP}. Update the issue's census row (Status, and Deps if changed) "
          f"in this branch first. If this commit is pure infra, omit the #NN.",
          file=sys.stderr)
    return 2  # deny


if __name__ == "__main__":
    sys.exit(main())
