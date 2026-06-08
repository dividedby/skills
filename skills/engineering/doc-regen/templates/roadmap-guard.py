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
# Branch(es) a PR may merge into. A list supports two-hop repos
# (feature→staging→main): list every base, and the roadmap counts as touched if
# it changed vs *any* of them. A bare string is still accepted.
BASE_BRANCH = ["main"]
# ---------------------------------------------------------------------------
ISSUE_REF = re.compile(r"#\d+")


def _base_branches() -> list[str]:
    """Normalize BASE_BRANCH to a list (a bare string is wrapped)."""
    if isinstance(BASE_BRANCH, str):
        return [BASE_BRANCH]
    return list(BASE_BRANCH)


def _changed() -> set[str] | None:
    """Files changed in this branch: staged, plus vs each base. Returns None
    when git is unusable for *every* probe (e.g. not a repo, no git) so the
    caller can fail open rather than deny on an undeterminable state."""
    files: set[str] = set()
    any_ok = False
    diffs = [["git", "diff", "--cached", "--name-only"]]
    diffs += [["git", "diff", "--name-only", f"{base}...HEAD"]
              for base in _base_branches()]
    for args in diffs:
        try:
            out = subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)
        except Exception:
            continue
        any_ok = True
        files.update(line.strip() for line in out.splitlines() if line.strip())
    return files if any_ok else None


def _enforced(cmd: str) -> bool:
    """Only an issue-referencing `git commit` is enforced."""
    return "git commit" in cmd and bool(ISSUE_REF.search(cmd))


def decide(cmd: str, changed: set[str] | None) -> int:
    """Pure deny/allow decision: 0 = allow, 2 = deny. Deny only when an
    issue-referencing commit leaves ROADMAP untouched across `changed`.
    `changed is None` (git undeterminable) fails open → allow."""
    if not _enforced(cmd):
        return 0
    if changed is None or ROADMAP in changed:
        return 0
    return 2


def main() -> int:
    try:
        cmd = (json.load(sys.stdin).get("tool_input", {}) or {}).get("command", "")
    except Exception:
        return 0  # fail open on malformed/absent input
    if not _enforced(cmd):
        return 0
    if decide(cmd, _changed()) == 0:
        return 0
    print(f"roadmap-guard: this commit references an issue but does not touch "
          f"{ROADMAP}. Update the issue's census row (Status, and Deps if changed) "
          f"in this branch first. If this commit is pure infra, omit the #NN.",
          file=sys.stderr)
    return 2  # deny


if __name__ == "__main__":
    sys.exit(main())
