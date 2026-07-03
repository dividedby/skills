"""Shared GitHub I/O layer for the fleet-drift checkers (#526).

`check_workflow_drift.py`, `check_label_drift.py`, and `check_idea_inbox_drift.py`
each read files from consumer repos via the GitHub Contents API and file a
dedup'd issue in `dividedby/skills` when drift is found. The plumbing for that
— running `gh`, fetching a file, ensuring a label exists, listing open issues,
and filing an issue — was byte-for-byte identical across all three; it lives
here once. Each script keeps its own REPOS map, ANCHORS/TIER_MARKERS, LABEL
constants, and drift-classification + issue-body logic — only the I/O core
is shared.
"""

import base64
import os
import subprocess
import sys
import tempfile
from typing import Optional

SKILLS_REPO = "dividedby/skills"


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


def ensure_label(
    label: str,
    color: str,
    description: str,
    write_token: str,
    dry_run: bool,
    repo: str = SKILLS_REPO,
) -> None:
    """Best-effort: create *label* in *repo* if absent."""
    if dry_run:
        print(f"[dry-run] would ensure label '{label}' in {repo}")
        return
    _gh(
        [
            "label", "create", label,
            "--repo", repo,
            "--color", color,
            "--description", description,
        ],
        token=write_token,
        check=False,  # exits non-zero if label already exists; that's fine
    )


def open_issues(label: str, write_token: str, repo: str = SKILLS_REPO) -> set[str]:
    """Return the set of open issue titles tagged *label* in *repo*."""
    result = _gh(
        [
            "issue", "list",
            "--repo", repo,
            "--label", label,
            "--state", "open",
            "--json", "title",
            "--jq", ".[].title",
        ],
        token=write_token,
        check=False,
    )
    if result.returncode != 0:
        # Can't read; treat as no open issues (worst case: duplicate filed).
        print(
            f"WARNING: could not fetch open issues: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return set()
    return set(result.stdout.strip().splitlines())


def file_issue(
    repo: str,
    title: str,
    body: str,
    label: str,
    write_token: str,
    dry_run: bool,
    dry_run_extra: Optional[list[str]] = None,
) -> None:
    """Open (or, in dry-run, print) an issue titled *title* with *label* in *repo*.

    *body* is the pre-built markdown body. *dry_run_extra* are additional
    lines printed after the title in dry-run mode (per-checker summary info).
    """
    if dry_run:
        print(f"[dry-run] would file issue in {repo}:")
        print(f"  title: {title}")
        for line in dry_run_extra or []:
            print(line)
        return

    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(body)
        body_path = fh.name
    try:
        result = _gh(
            [
                "issue", "create",
                "--repo", repo,
                "--title", title,
                "--body-file", body_path,
                "--label", label,
            ],
            token=write_token,
        )
        url = result.stdout.strip().splitlines()[-1]
        print(f"Filed: {url}")
    finally:
        os.unlink(body_path)


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
