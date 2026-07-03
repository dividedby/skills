"""Fleet-wide REPORT-ONLY idea-inbox.md drift detector.

Reads each carrier repo's ``docs/agents/idea-inbox.md`` via the GitHub API and
checks for eight canonical structural anchors. Opens a single ``idea-inbox-drift``
issue in dividedby/skills per drifted repo, naming ``setup-dividedby-skills`` as
the fixer. Never mutates a carrier repo.

Prerequisites
-------------
- ISSUES_TOKEN: fine-grained PAT, owner dividedby, all repositories,
  Contents:Read + Issues:Write. Passed as --read-token.
  Until the secret is created the job exits 0 and does nothing (graceful no-op).

Usage
-----
    python3 tools/check_idea_inbox_drift.py \\
        --read-token <PAT>  \\
        --write-token <GITHUB_TOKEN> \\
        [--dry-run]
"""

import argparse
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

# Carrier repos (non-canonical copies of idea-inbox.md) mapped to their
# default branch.  Confirmed 2026-06-29 via
# `gh repo view dividedby/<repo> --json defaultBranchRef`.
# dividedby/skills is the canonical source — excluded from this map.
# ponytail: archived repos dropped by hand; verify via
#   gh api repos/<r> -q .archived if more get archived.
REPOS: dict[str, str] = {
    "dividedby/infra": "main",
    "dividedby/agent-research": "main",
    "dividedby/claude-config": "main",
    "dividedby/dokdiv": "main",
    "dividedby/dokploy-maintenance": "main",
    "dividedby/General-URL-Cleaner-Revived": "main",
    "dividedby/goodreads-bot": "staging",
    "dividedby/moodreader": "main",
    "dividedby/rtings-links": "main",
}

SKILLS_REPO = "dividedby/skills"
SKILLS_REPO_WRITE = SKILLS_REPO  # issues are always filed here

INBOX_PATH = "docs/agents/idea-inbox.md"

# Each anchor is (human-readable name, marker substring).
# An anchor is PRESENT if its marker appears anywhere in the file content.
# No anchor depends on a specific label-doc filename — `triage-labels.md`
# variants are tolerated by construction.
# ponytail: presence-substring heuristic — stable short substrings, not full
# prose phrases. If a future reword ever false-positives, escalate to a
# numbered-list/section parse rather than lengthening the marker.
ANCHORS: list[tuple[str, str]] = [
    ("agent-protocol breadcrumb",               "agent-protocol:"),
    ("drain step 1 (Dedup / relate)",            "Dedup"),
    ("drain step 2 (Decision-map)",              "Decision-map"),
    ("drain step 3 (Pick only the steps it needs)", "Pick only the steps"),
    ("drain step 4 (Labels)",                    "**Labels**"),
    ("drain step 5 (Aim for a strong agent brief)", "strong agent brief"),
    ("drain step 6 (Move to Actioned)",          "Move to Actioned"),
    ("Actioned rolling-window section",          "Actioned rolling window"),
]

LABEL = "idea-inbox-drift"
LABEL_COLOR = "1D76DB"  # blue; distinct from workflow-drift (rose) and label-drift (orange-red)
LABEL_DESCRIPTION = "idea-inbox.md has drifted from the canonical dividedby structure"


# ---------------------------------------------------------------------------
# Drift classification (pure; no I/O)
# ---------------------------------------------------------------------------


def classify_drift(content: str) -> list[str]:
    """Return names of structural anchors missing from *content*.

    An empty list means the file is canonical. Each name corresponds to an
    entry in ANCHORS; callers use the list directly for issue body prose.
    """
    return [name for name, marker in ANCHORS if marker not in content]


# ---------------------------------------------------------------------------
# Issue helpers (pure; no I/O)
# ---------------------------------------------------------------------------


def _issue_title(repo: str) -> str:
    """Deterministic issue title for a drifted repo (used for dedup and create)."""
    short = repo.split("/")[-1]
    return f"[idea-inbox-drift] {short}: idea-inbox.md has drifted"


def build_issue_body(repo: str, missing: list[str]) -> str:
    """Build the markdown body for an idea-inbox-drift issue.

    Names ``setup-dividedby-skills`` as the fixer and references #489 for
    the one-time bulk reconciliation of pre-existing drift.
    """
    anchor_list = "\n".join(f"- {name}" for name in missing)
    lines = [
        f"## Idea-inbox drift detected in `{repo}`",
        "",
        "This is an automated report from the weekly `check-idea-inbox-drift` job",
        "([`tools/check_idea_inbox_drift.py`](../../tools/check_idea_inbox_drift.py)).",
        "",
        f"`{INBOX_PATH}` in this repo is missing one or more canonical structural anchors:",
        "",
        anchor_list,
        "",
        "### What to do",
        "",
        "Run **`setup-dividedby-skills`** against this repo. That skill's",
        "onboarding reconciles the idea-inbox doc to the canonical dividedby",
        f"structure (seeded from `dividedby/skills {INBOX_PATH}`).",
        "",
        "For the one-time bulk reconciliation of existing drift across the fleet,",
        "see [#489](https://github.com/dividedby/skills/issues/489).",
        "",
        "Reference: [`docs/agents/idea-inbox.md`](../../docs/agents/idea-inbox.md),",
        "[`skills/config/setup-dividedby-skills/SKILL.md`](../../skills/config/setup-dividedby-skills/SKILL.md).",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
#
# fetch_file, ensure_label, open_issues are shared with check_workflow_drift.py
# and check_label_drift.py — see tools/_drift_common.py (#526).


def file_issue(
    repo: str,
    missing: list[str],
    write_token: str,
    dry_run: bool,
) -> None:
    """Open or print an idea-inbox-drift issue for *repo* in skills."""
    title = _issue_title(repo)
    body = build_issue_body(repo, missing)
    _file_issue_io(
        SKILLS_REPO_WRITE, title, body, LABEL, write_token, dry_run,
        [f"  missing: {missing}"],
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check carrier repos' idea-inbox.md for structural drift."
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

    for repo, branch in REPOS.items():
        try:
            content = fetch_file(repo, branch, INBOX_PATH, read_token)
        except RuntimeError as exc:
            print(f"ERROR fetching {repo}/{INBOX_PATH}: {exc}", file=sys.stderr)
            any_error = True
            continue

        if content is None:
            missing = [name for name, _ in ANCHORS]  # all anchors absent
            print(f"DRIFT: {repo}: file absent (all anchors missing)")
        else:
            missing = classify_drift(content)

        if not missing:
            print(f"OK:    {repo}")
            continue

        if content is not None:
            print(f"DRIFT: {repo}: missing {missing}")

        title = _issue_title(repo)
        if title in open_titles:
            print(f"SKIP:  issue already open for {repo} (dedup)")
        else:
            file_issue(repo, missing, write_token, args.dry_run)

    if any_error:
        sys.exit(1)
    # Always exit 0 on drift found — this is a report, not a gate.
    sys.exit(0)


if __name__ == "__main__":
    main()
