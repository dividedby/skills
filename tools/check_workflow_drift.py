"""Divergence-detection guard for vendored Claude-powered workflow files.

Reads each consumer repo's vendored workflow files via the GitHub API and
checks each against a set of required structural anchors. Opens a single
``workflow-drift`` issue in dividedby/skills per drifted repo. Report only
— never a hard CI gate, never auto-fix.

Prerequisites
-------------
- ISSUES_TOKEN: fine-grained PAT, owner dividedby, all repositories,
  Contents:Read + Issues:Write. Passed as --read-token.
  Until the secret is created the job exits 0 and does nothing (graceful no-op).

Usage
-----
    python3 tools/check_workflow_drift.py \\
        --read-token <PAT>  \\
        --write-token <GITHUB_TOKEN> \\
        [--dry-run]
"""

import argparse
import os
import sys

try:
    from tools._drift_common import ensure_label, fetch_file, open_issues
    from tools._drift_common import file_issue as _file_issue_io
except ImportError:
    from _drift_common import ensure_label, fetch_file, open_issues
    from _drift_common import file_issue as _file_issue_io

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Repos to audit, mapped to their default branch.
# Confirmed 2026-06-20 via `gh repo view dividedby/<repo> --json defaultBranchRef`.
# ponytail: archived repos dropped by hand; if more get archived, skip via
#   gh api repos/<r> -q .archived
REPOS: dict[str, str] = {
    "dividedby/moodreader": "main",
    "dividedby/agent-research": "main",
    "dividedby/goodreads-bot": "staging",
}

# The skills repo itself (used as a local-read canary; not in REPOS because
# skills' own caller stubs use a local `./` ref, not `@claude-loops-v1`).
SKILLS_REPO = "dividedby/skills"
SKILLS_BRANCH = "main"

# Workflow paths relative to repo root.
APPLY_PATH = ".github/workflows/apply-agent-research.yml"
ARCH_PATH = ".github/workflows/improve-codebase-architecture.yml"
STALE_PATH = ".github/workflows/staleness-review.yml"

# Reusable body paths (local to skills; not vendored to consumers).
ARCH_BODY_PATH = ".github/workflows/improve-codebase-architecture-reusable.yml"
STALE_BODY_PATH = ".github/workflows/staleness-review-reusable.yml"
APPLY_BODY_PATH = ".github/workflows/apply-agent-research-reusable.yml"

# Anchor sets: substrings that MUST appear in every non-missing file.
#
# apply-agent-research.yml (thin caller stubs — consumer repos + skills canary):
#   - "permissions:" + "issues: write" → missing == #384 startup-fail class
#   - "@claude-loops-v1" → missing == stub points at wrong ref or is full-copy OLD-gen
#     (skipped for skills canary via SKILLS_SKIP_ANCHORS — it uses local `./` ref)
#   - "CLAUDE_CODE_OAUTH_TOKEN" → missing == token not passed through
#
# improve-codebase-architecture.yml (consumer stubs only, not skills canary):
#   - "permissions:" + "issues: write" → startup-fail class (#384)
#   - "@claude-loops-v1" → missing == stub points at wrong ref or is full-copy OLD-gen
#   - "CLAUDE_CODE_OAUTH_TOKEN" → missing == token not passed through
#
# staleness-review.yml (consumer stubs only, not skills canary):
#   same as improve-codebase-architecture stubs

ANCHORS: dict[str, list[str]] = {
    APPLY_PATH: [
        "permissions:",
        "issues: write",
        "@claude-loops-v1",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ],
    ARCH_PATH: [
        "permissions:",
        "issues: write",
        "@claude-loops-v1",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ],
    STALE_PATH: [
        "permissions:",
        "issues: write",
        "@claude-loops-v1",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ],
}

# Anchors for the reusable body files (local to skills; hardened form — C-1/C-2/C-3).
#
# C-1 — SHA-pinned actions: no movable tag (actions/checkout@v + digit is the old form).
# C-2 — acceptEdits absent: proposal loops must not carry --permission-mode acceptEdits.
# C-3 — scoped allowedTools: no bare Bash(git:*) or Bash(python3:*) wildcard.
#   - "Bash(git log:*)" is the narrowest read-only git anchor present in both bodies.
#   - "Bash(python3 $SKILL_DIR" is present only in staleness-review (scoped to lib/).
#     arch-review has no python3 tool grant — its absence is verified by asserting
#     "Bash(python3:*)" does NOT appear (checked as a "must-not" anchor separately below).
BODY_ANCHORS: dict[str, list[str]] = {
    ARCH_BODY_PATH: [
        "permissions:",
        "issues: write",
        "--model claude-sonnet-5",
        "--max-budget-usd",
        "--output-format stream-json",
        "git clone --depth 1",
        # C-1: SHA-pinned checkout (40-char hex after @).
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
        # C-3: scoped git (at least one specific read-only subcommand present).
        "Bash(git log:*)",
    ],
    STALE_BODY_PATH: [
        "permissions:",
        "issues: write",
        "--model claude-sonnet-5",
        "--max-budget-usd",
        "--output-format stream-json",
        "git clone --depth 1",
        # C-1: SHA-pinned checkout.
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
        # C-3: scoped git and scoped python3.
        "Bash(git log:*)",
        "Bash(python3 $SKILL_DIR/lib/:*)",
    ],
    APPLY_BODY_PATH: [
        "permissions:",
        "issues: write",
        "--model claude-sonnet-5",
        "--max-budget-usd",
        "--output-format stream-json",
        "git clone --depth 1",
        # C-1: SHA-pinned checkout (40-char hex after @).
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
        # C-3: scoped git (at least one specific read-only subcommand present).
        "Bash(git log:*)",
        # C-3: scoped python3 (skill's own cli.py).
        "Bash(python3 $SKILL_DIR/lib/cli.py:*)",
        # Harness prompt fetched fresh from the skills clone (not from local checkout).
        # The file uses $HARNESS/prompts/apply-agent-research.md — match the path suffix.
        "prompts/apply-agent-research.md",
    ],
}

# Must-NOT-appear anchors for the reusable bodies (hardened form violations).
BODY_FORBIDDEN: dict[str, list[str]] = {
    ARCH_BODY_PATH: [
        "--permission-mode acceptEdits",  # C-2: no acceptEdits in propose-only loop
        "Bash(git:*)",                    # C-3: bare git wildcard replaced by scoped subcommands
        "Bash(python3:*)",               # C-3: arch-review has no python3 grant
        "actions/checkout@v",            # C-1: movable tag replaced by SHA pin
        "Bash(gh search:*)",             # C-3: prompt uses only gh issue list/view; search not needed
        "Bash(gh api:*)",                # C-3: write primitive — bypasses proposal cap (#306)
    ],
    STALE_BODY_PATH: [
        "--permission-mode acceptEdits",  # C-2: no acceptEdits in propose-only loop
        "Bash(git:*)",                    # C-3: bare git wildcard replaced by scoped subcommands
        "Bash(python3:*)",               # C-3: bare python3 wildcard replaced by scoped path
        "actions/checkout@v",            # C-1: movable tag replaced by SHA pin
        "Bash(gh search:*)",             # C-3: prompt uses only gh issue list/view; search not needed
        "Bash(gh api:*)",                # C-3: write primitive — bypasses proposal cap (#306)
    ],
    APPLY_BODY_PATH: [
        "--permission-mode acceptEdits",  # C-2: no acceptEdits — loop files via guarded cli.py shim
        "Bash(git:*)",                    # C-3: bare git wildcard replaced by scoped subcommands
        "Bash(python3:*)",               # C-3: bare python3 wildcard replaced by scoped path
        "actions/checkout@v",            # C-1: movable tag replaced by SHA pin
        "Bash(gh api:*)",                # C-3: write primitive — bypasses proposal cap (#306)
    ],
}

# Anchors to skip when checking skills' OWN caller stubs.  Skills uses a local
# `./` ref by design (canary — always runs the latest body) rather than
# @claude-loops-v1, so that tag is not expected there.
SKILLS_SKIP_ANCHORS: set[str] = {"@claude-loops-v1"}

LABEL = "workflow-drift"
LABEL_COLOR = "E11D48"  # red-ish; distinct from the purple proposal labels
LABEL_DESCRIPTION = "Vendored workflow has drifted from required structural anchors"
SKILLS_REPO_WRITE = SKILLS_REPO  # issues are always filed here

# ---------------------------------------------------------------------------
# Pure helpers (unit-tested; no I/O)
# ---------------------------------------------------------------------------


def check_file(content: str, anchors: list[str], skip: set[str] | None = None) -> list[str]:
    """Return the list of anchors missing from *content*.

    Args:
        content: The decoded text of the workflow file.
        anchors: Required substrings.
        skip:    Anchors to ignore (used for the skills canary stubs).

    Returns:
        Ordered list of missing anchors (empty == clean).
    """
    skip = skip or set()
    return [a for a in anchors if a not in skip and a not in content]


def check_forbidden(content: str, forbidden: list[str]) -> list[str]:
    """Return the list of forbidden substrings that ARE present in *content*.

    Used to enforce hardened-form must-not-appear rules (C-2, C-3).

    Args:
        content:   The decoded text of the workflow file.
        forbidden: Substrings that must NOT appear.

    Returns:
        Ordered list of violated (present) forbidden substrings (empty == clean).
    """
    return [f for f in forbidden if f in content]


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
#
# fetch_file, ensure_label, open_issues are shared with check_label_drift.py
# and check_idea_inbox_drift.py — see tools/_drift_common.py (#526).


def _issue_title(repo: str) -> str:
    """Deterministic issue title for a drifted repo (used for dedup and create)."""
    short = repo.split("/")[-1]
    return f"[workflow-drift] {short}: vendored workflows have diverged"


def build_issue_body(repo: str, drifted: dict[str, list[str]]) -> str:
    """Build the markdown body for a workflow-drift issue.

    *drifted* maps filename → list of missing anchors.
    """
    lines = [
        f"## Workflow drift detected in `{repo}`",
        "",
        "The following vendored workflow files are missing required structural anchors.",
        "This is an automated report from the weekly `check-workflow-drift` job",
        "([`tools/check_workflow_drift.py`](../../tools/check_workflow_drift.py)).",
        "",
    ]
    for path, missing in sorted(drifted.items()):
        lines.append(f"### `{path}`")
        lines.append("")
        lines.append("Missing anchors:")
        for anchor in missing:
            lines.append(f"- `{anchor}`")
        lines.append("")
    lines += [
        "### What to do",
        "",
        "1. Open the file in the repo and compare it against the canonical version in `dividedby/skills`.",
        "2. Restore any missing anchors (or confirm they were intentionally removed and update the anchor set).",
        "3. Close this issue once the file is clean.",
        "",
        "Reference: [`docs/agents/vendored-workflows.md`](../../docs/agents/vendored-workflows.md),",
        "[ADR 0014](../../docs/adr/0014-harness-is-fetched-fresh-only-the-workflow-envelope-is-vendored.md).",
    ]
    return "\n".join(lines)


def file_issue(
    repo: str, drifted: dict[str, list[str]], write_token: str, dry_run: bool
) -> None:
    """Open or print a drift issue for *repo* in skills.

    *drifted* maps filename → list of missing anchors.
    """
    title = _issue_title(repo)
    body = build_issue_body(repo, drifted)
    dry_run_extra = [
        f"  {path}: missing {missing}" for path, missing in sorted(drifted.items())
    ]
    _file_issue_io(
        SKILLS_REPO_WRITE, title, body, LABEL, write_token, dry_run, dry_run_extra
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check vendored Claude workflow files for structural drift."
    )
    parser.add_argument("--read-token", default="", help="PAT for cross-repo Contents:Read")
    parser.add_argument("--write-token", default="", help="Token for Issues:Write in skills")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be filed; make no mutating API calls",
    )
    args = parser.parse_args(argv)

    read_token = args.read_token.strip()
    write_token = args.write_token.strip()

    if not read_token:
        print(
            "NOTICE: --read-token empty/absent. Exiting without checking (inert no-op until the secret exists).",
            file=sys.stderr,
        )
        sys.exit(0)

    if not write_token:
        write_token = read_token  # fallback: use the same token for both

    # Ensure the label exists before we need it.
    ensure_label(LABEL, LABEL_COLOR, LABEL_DESCRIPTION, write_token, args.dry_run)

    # Fetch open drift issues once (used for dedup across all repos).
    if args.dry_run:
        open_titles: set[str] = set()
    else:
        open_titles = open_issues(LABEL, write_token)

    any_error = False

    # Check consumer repos.
    for repo, branch in REPOS.items():
        drifted: dict[str, list[str]] = {}
        for path, anchors in ANCHORS.items():
            try:
                content = fetch_file(repo, branch, path, read_token)
            except RuntimeError as exc:
                print(f"ERROR fetching {repo}/{path}: {exc}", file=sys.stderr)
                any_error = True
                continue

            if content is None:
                print(f"WARN: {repo}/{path} not found (missing file is drift)")
                drifted[path] = [f"<file missing — expected at {path}>"]
                continue

            missing = check_file(content, anchors)
            if missing:
                print(f"DRIFT: {repo}/{path}: missing {missing}")
                drifted[path] = missing
            else:
                print(f"OK:    {repo}/{path}")

        if drifted:
            title = _issue_title(repo)
            if title in open_titles:
                print(f"SKIP:  issue already open for {repo} (dedup)")
            else:
                file_issue(repo, drifted, write_token, args.dry_run)

    # Check skills' own caller stubs (canary; skip @claude-loops-v1 anchor).
    # APPLY_PATH is included here: it's a thin local-`./` caller (ADR 0029), so
    # @claude-loops-v1 is not expected and is skipped via SKILLS_SKIP_ANCHORS.
    for path in (ARCH_PATH, STALE_PATH, APPLY_PATH):
        anchors = ANCHORS[path]
        try:
            content = fetch_file(SKILLS_REPO, SKILLS_BRANCH, path, read_token)
        except RuntimeError as exc:
            print(f"ERROR fetching {SKILLS_REPO}/{path}: {exc}", file=sys.stderr)
            any_error = True
            continue

        if content is None:
            print(f"WARN: {SKILLS_REPO}/{path} not found")
            continue

        missing = check_file(content, anchors, skip=SKILLS_SKIP_ANCHORS)
        if missing:
            print(f"DRIFT: {SKILLS_REPO}/{path}: missing {missing}")
        else:
            print(f"OK:    {SKILLS_REPO}/{path}")

    # skills' own apply-agent-research.yml — also verify local file (canary).
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_apply = os.path.join(repo_root, APPLY_PATH)
    try:
        with open(local_apply, encoding="utf-8") as fh:
            skills_apply_content = fh.read()
        missing = check_file(skills_apply_content, ANCHORS[APPLY_PATH], skip=SKILLS_SKIP_ANCHORS)
        if missing:
            print(f"DRIFT: {SKILLS_REPO}/{APPLY_PATH} (local): missing {missing}")
        else:
            print(f"OK:    {SKILLS_REPO}/{APPLY_PATH} (local)")
    except OSError as exc:
        print(f"ERROR reading local {APPLY_PATH}: {exc}", file=sys.stderr)
        any_error = True

    # skills' own reusable bodies — check hardened form (C-1/C-2/C-3 anchors).
    for body_path in (ARCH_BODY_PATH, STALE_BODY_PATH, APPLY_BODY_PATH):
        local_body = os.path.join(repo_root, body_path)
        try:
            with open(local_body, encoding="utf-8") as fh:
                body_content = fh.read()
        except OSError as exc:
            print(f"ERROR reading local {body_path}: {exc}", file=sys.stderr)
            any_error = True
            continue

        missing = check_file(body_content, BODY_ANCHORS[body_path])
        present_forbidden = check_forbidden(body_content, BODY_FORBIDDEN[body_path])
        if missing:
            print(f"DRIFT: {SKILLS_REPO}/{body_path}: missing required anchors {missing}")
        if present_forbidden:
            print(f"DRIFT: {SKILLS_REPO}/{body_path}: forbidden patterns present {present_forbidden}")
        if not missing and not present_forbidden:
            print(f"OK:    {SKILLS_REPO}/{body_path}")

    if any_error:
        sys.exit(1)
    # Always exit 0 on drift found — this is a report, not a gate.
    sys.exit(0)


if __name__ == "__main__":
    main()
