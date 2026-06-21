"""Divergence-detection guard for vendored Claude-powered workflow files.

Reads each consumer repo's vendored workflow files via the GitHub API and
checks each against a set of required structural anchors. Opens a single
``workflow-drift`` issue in dividedby/skills per drifted repo. Report only
— never a hard CI gate, never auto-fix.

Prerequisites
-------------
- DRIFT_CHECK_TOKEN: fine-grained PAT, owner dividedby, repositories:
  moodreader + agent-research + goodreads-bot + tweakcc-maint + skills,
  Contents:Read + Issues:Write on skills. Until this secret is created the
  job exits 0 and does nothing (graceful no-op).

Usage
-----
    python3 tools/check_workflow_drift.py \\
        --read-token <PAT>  \\
        --write-token <GITHUB_TOKEN> \\
        [--dry-run]
"""

import argparse
import base64
import os
import subprocess
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Repos to audit, mapped to their default branch.
# Confirmed 2026-06-20 via `gh repo view dividedby/<repo> --json defaultBranchRef`.
REPOS: dict[str, str] = {
    "dividedby/moodreader": "main",
    "dividedby/agent-research": "main",
    "dividedby/goodreads-bot": "staging",
    "dividedby/tweakcc-maint": "main",
}

# The skills repo itself (used as a local-read canary; not in REPOS because
# skills' own caller stubs use a local `./` ref, not `@claude-loops-v1`).
SKILLS_REPO = "dividedby/skills"
SKILLS_BRANCH = "main"

# Workflow paths relative to repo root.
APPLY_PATH = ".github/workflows/apply-agent-research.yml"
ARCH_PATH = ".github/workflows/improve-codebase-architecture.yml"
STALE_PATH = ".github/workflows/staleness-review.yml"

# Anchor sets: substrings that MUST appear in every non-missing file.
#
# apply-agent-research.yml — variant-neutral (host / consumer / producer all share):
#   - "permissions:" + "issues: write" → missing == #384 startup-fail class
#   - "harness/prompts/apply-agent-research.md" → prompt fetched fresh; present in all 5
#     variants (consumer/host via RUNNER_TEMP/skills-src/harness/prompts/…; host via
#     local checkout). NOTE: "harness/cli.py" is deliberately excluded — the producer
#     (agent-research) uses only the skill's own lib/cli.py, not harness/cli.py; only
#     consumers + host reference it. harness/prompts/ catches OLD-gen without this gap.
#   - "--model claude-sonnet-4-6" → missing == floating alias, silent model upgrade
#   - "--max-budget-usd" → missing == no spend backstop
#   - "--output-format stream-json" → missing == no cost ledger line emitted
#   - "git clone --depth 1" → missing == no shallow clone at all (harness not fetched)
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
        "harness/prompts/apply-agent-research.md",
        "--model claude-sonnet-4-6",
        "--max-budget-usd",
        "--output-format stream-json",
        "git clone --depth 1",
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


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _gh(args: list[str], token: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a ``gh`` subprocess with GH_TOKEN set to *token*."""
    # Inherit PATH and HOME so gh can find its config.
    full_env = {**os.environ, "GH_TOKEN": token}
    return subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        check=check,
        env=full_env,
    )


def fetch_file(repo: str, branch: str, path: str, read_token: str) -> Optional[str]:
    """Fetch *path* from *repo* at *branch* via the GitHub Contents API.

    Returns decoded text on success, or ``None`` if the file is missing (404).
    Raises ``RuntimeError`` on any other error.
    """
    api_path = f"repos/{repo}/contents/{path}"
    result = _gh(
        ["api", f"{api_path}?ref={branch}", "--jq", ".content"],
        token=read_token,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "404" in stderr or "Not Found" in stderr:
            return None
        raise RuntimeError(
            f"gh api {api_path}: exit {result.returncode}: {stderr}"
        )
    encoded = result.stdout.strip()
    if not encoded:
        return None
    # GitHub returns base64 with embedded newlines; strip them.
    decoded = base64.b64decode(encoded.replace("\n", "")).decode("utf-8")
    return decoded


def ensure_label(write_token: str, dry_run: bool) -> None:
    """Best-effort: create the workflow-drift label in skills if absent."""
    if dry_run:
        print(f"[dry-run] would ensure label '{LABEL}' in {SKILLS_REPO_WRITE}")
        return
    _gh(
        [
            "label", "create", LABEL,
            "--repo", SKILLS_REPO_WRITE,
            "--color", LABEL_COLOR,
            "--description", LABEL_DESCRIPTION,
        ],
        token=write_token,
        check=False,  # exits non-zero if label already exists; that's fine
    )


def open_issues_for_repo(repo: str, write_token: str) -> set[str]:
    """Return the set of open issue titles tagged workflow-drift for *repo*."""
    result = _gh(
        [
            "issue", "list",
            "--repo", SKILLS_REPO_WRITE,
            "--label", LABEL,
            "--state", "open",
            "--json", "title",
            "--jq", ".[].title",
        ],
        token=write_token,
        check=False,
    )
    if result.returncode != 0:
        # Can't read; treat as no open issues (worst case: duplicate filed).
        print(f"WARNING: could not fetch open issues: {result.stderr.strip()}", file=sys.stderr)
        return set()
    return set(result.stdout.strip().splitlines())


def _issue_title(repo: str) -> str:
    """Deterministic issue title for a drifted repo (used for dedup and create)."""
    short = repo.split("/")[-1]
    return f"[workflow-drift] {short}: vendored workflows have diverged"


def file_issue(repo: str, drifted: dict[str, list[str]], write_token: str, dry_run: bool) -> None:
    """Open or print a drift issue for *repo* in skills.

    *drifted* maps filename → list of missing anchors.
    """
    title = _issue_title(repo)
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
    body = "\n".join(lines)

    if dry_run:
        print(f"[dry-run] would file issue in {SKILLS_REPO_WRITE}:")
        print(f"  title: {title}")
        for path, missing in sorted(drifted.items()):
            print(f"  {path}: missing {missing}")
        return

    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(body)
        body_path = fh.name
    try:
        result = _gh(
            [
                "issue", "create",
                "--repo", SKILLS_REPO_WRITE,
                "--title", title,
                "--body-file", body_path,
                "--label", LABEL,
            ],
            token=write_token,
        )
        url = result.stdout.strip().splitlines()[-1]
        print(f"Filed: {url}")
    finally:
        os.unlink(body_path)


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
            "NOTICE: --read-token is empty. DRIFT_CHECK_TOKEN secret has not been created yet. "
            "Exiting without checking (inert no-op until the secret exists).",
            file=sys.stderr,
        )
        sys.exit(0)

    if not write_token:
        write_token = read_token  # fallback: use the same token for both

    # Ensure the label exists before we need it.
    ensure_label(write_token, args.dry_run)

    # Fetch open drift issues once (used for dedup across all repos).
    if args.dry_run:
        open_titles: set[str] = set()
    else:
        open_titles = open_issues_for_repo(SKILLS_REPO_WRITE, write_token)

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
    for path in (ARCH_PATH, STALE_PATH):
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

    # skills' own apply-agent-research.yml — read local file.
    local_apply = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        APPLY_PATH,
    )
    try:
        with open(local_apply, encoding="utf-8") as fh:
            skills_apply_content = fh.read()
        missing = check_file(skills_apply_content, ANCHORS[APPLY_PATH])
        if missing:
            print(f"DRIFT: {SKILLS_REPO}/{APPLY_PATH}: missing {missing}")
        else:
            print(f"OK:    {SKILLS_REPO}/{APPLY_PATH}")
    except OSError as exc:
        print(f"ERROR reading local {APPLY_PATH}: {exc}", file=sys.stderr)
        any_error = True

    if any_error:
        sys.exit(1)
    # Always exit 0 on drift found — this is a report, not a gate.
    sys.exit(0)


if __name__ == "__main__":
    main()
